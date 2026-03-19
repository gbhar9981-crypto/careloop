import os
import boto3
import json
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional

from . import models, schemas, auth, database

# Create tables
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Careloop+ Backend")

# --- Auto-Migration: Add missing columns ---
@app.on_event("startup")
def run_migrations():
    """Automatically add any missing columns to existing tables."""
    try:
        with database.engine.connect() as conn:
            # Check and add 'is_taken' to medicines
            result = conn.execute(
                database.text("SHOW COLUMNS FROM medicines LIKE 'is_taken'")
            )
            if result.fetchone() is None:
                conn.execute(
                    database.text("ALTER TABLE medicines ADD COLUMN is_taken BOOLEAN DEFAULT FALSE")
                )
                conn.commit()
                print("✅ Migration: added 'is_taken' to medicines table.")
    except Exception as e:
        print(f"⚠️  Migration warning: {e}")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Amazon Bedrock Setup ---
try:
    bedrock_runtime = boto3.client(
        service_name='bedrock-runtime',
        region_name='us-east-1', # Change to your region
        aws_access_key_id="AKIAQR2536KGTTF4CZ4N",
        aws_secret_access_key="2wm55WWAQz/YuD/e9ETCkd8/q2rRWB7R+PrBCs9i",
    )
except Exception as e:
    print(f"Bedrock initialization error: {e}")
    bedrock_runtime = None

# --- Authentication ---

@app.post("/api/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = auth.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(email=user.email, name=user.name, hashed_password=hashed_password, role=user.role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/api/login")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = auth.get_user_by_email(db, email=form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = auth.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "user_id": user.id,
        "name": user.name,
        "role": user.role
    }

@app.put("/api/users/me", response_model=schemas.UserResponse)
def update_user_profile(
    user_update: schemas.UserUpdate, 
    db: Session = Depends(database.get_db), 
    current_user: models.User = Depends(auth.get_current_user)
):
    if user_update.name is not None:
        current_user.name = user_update.name
    if user_update.age is not None:
        current_user.age = user_update.age
    if user_update.blood_group is not None:
        current_user.blood_group = user_update.blood_group
    if user_update.condition is not None:
        current_user.condition = user_update.condition
    if user_update.allergies is not None:
        current_user.allergies = user_update.allergies
        
    db.commit()
    db.refresh(current_user)
    return current_user

# --- Mock Data ---

@app.get("/api/doctors", response_model=List[schemas.DoctorResponse])
def get_doctors(db: Session = Depends(database.get_db)):
    doctors = db.query(models.User).filter(models.User.role == "doctor").all()
    return [
        {
            "id": d.id, 
            "name": d.name, 
            "specialty": "General Physician", 
            "hospital": "Careloop Network", 
            "rating": 5.0
        } for d in doctors
    ]

@app.get("/api/conditions", response_model=List[schemas.ConditionResponse])
def get_conditions():
    return [
        {"id": 1, "name": "Hypertension", "description": "High blood pressure condition.", "symptoms": ["Headaches", "Shortness of breath", "Nosebleeds"]},
        {"id": 2, "name": "Type 2 Diabetes", "description": "Chronic condition that affects the way the body processes blood sugar.", "symptoms": ["Increased thirst", "Frequent urination", "Fatigue"]},
        {"id": 3, "name": "Asthma", "description": "A condition in which your airways narrow and swell.", "symptoms": ["Shortness of breath", "Chest tightness", "Wheezing"]},
    ]

@app.get("/api/hospitals", response_model=List[schemas.HospitalResponse])
def get_hospitals():
    return [
        {"id": 1, "name": "City General Hospital", "address": "123 Main St, Cityville", "lat": 40.7128, "lng": -74.0060},
        {"id": 2, "name": "Westside Clinic", "address": "456 West Ave, Cityville", "lat": 40.7200, "lng": -74.0100},
        {"id": 3, "name": "Careloop Medical Center", "address": "789 Health Blvd, Cityville", "lat": 40.7300, "lng": -73.9900},
    ]

# --- Medicines ---

@app.get("/api/medicines", response_model=List[schemas.MedicineResponse])
def get_medicines(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.Medicine).filter(models.Medicine.user_id == current_user.id).all()

@app.post("/api/medicines", response_model=schemas.MedicineResponse)
def create_medicine(medicine: schemas.MedicineCreate, patient_id: Optional[int] = None, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    target_user_id = current_user.id
    if current_user.role == "doctor" and patient_id is not None:
        target_user_id = patient_id
        
    db_medicine = models.Medicine(**medicine.model_dump(), user_id=target_user_id)
    db.add(db_medicine)
    db.commit()
    db.refresh(db_medicine)
    return db_medicine

@app.delete("/api/medicines/{medicine_id}")
def delete_medicine(medicine_id: int, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_med = db.query(models.Medicine).filter(models.Medicine.id == medicine_id, models.Medicine.user_id == current_user.id).first()
    if not db_med:
        raise HTTPException(status_code=404, detail="Medicine not found")
    
    db.delete(db_med)
    db.commit()
    return {"detail": "Medicine deleted"}

@app.put("/api/medicines/{medicine_id}/take")
def take_medicine(medicine_id: int, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_med = db.query(models.Medicine).filter(models.Medicine.id == medicine_id, models.Medicine.user_id == current_user.id).first()
    if not db_med:
        raise HTTPException(status_code=404, detail="Medicine not found")
    
    db_med.is_taken = True
    db.commit()
    return {"detail": "Medicine marked as taken"}

# --- Reviews ---

@app.post("/api/reviews", response_model=schemas.ReviewResponse)
def submit_review(review: schemas.ReviewCreate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_review = models.Review(**review.model_dump(), user_id=current_user.id)
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review

# --- Patient Reports & Management ---

@app.get("/api/patients")
def get_patients(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can view the patient list")
    
    links = db.query(models.PatientDoctorLink).filter(
        models.PatientDoctorLink.doctor_id == current_user.id,
        models.PatientDoctorLink.status == "accepted"
    ).all()
    patient_ids = [link.patient_id for link in links]
    
    patients = db.query(models.User).filter(models.User.id.in_(patient_ids)).all()
    
    result = []
    for p in patients:
        latest_vital = db.query(models.Vital).filter(models.Vital.patient_id == p.id).order_by(models.Vital.recorded_at.desc()).first()
        status = "Stable"
        if latest_vital and (int(latest_vital.bp.split('/')[0]) > 140 or latest_vital.oxygen < 95):
            status = "Critical"
            
        result.append({
            "id": p.id,
            "name": p.name,
            "condition": p.condition or "Unknown",
            "status": status,
            "latest_bp": latest_vital.bp if latest_vital else "N/A",
            "latest_hr": latest_vital.pulse if latest_vital else "N/A"
        })
    return result

@app.get("/api/reports/{patient_id}")
def get_patient_report(patient_id: int, db: Session = Depends(database.get_db)):
    # Dynamically generate the report based on the real patient/user registered
    user = db.query(models.User).filter(models.User.id == patient_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Patient report not found")
        
    medicines = db.query(models.Medicine).filter(models.Medicine.user_id == user.id).all()
    prescriptions = [{"medicine": m.name, "dosage": m.dosage, "frequency": m.time_to_take, "is_taken": m.is_taken} for m in medicines]
    
    vitals = db.query(models.Vital).filter(models.Vital.patient_id == user.id).order_by(models.Vital.recorded_at.desc()).limit(5).all()
    vitals_data = [{"bp": v.bp, "pulse": v.pulse, "oxygen": v.oxygen, "temperature": v.temperature, "date": v.recorded_at.isoformat()} for v in vitals]
    
    appointments = db.query(models.Appointment).filter(models.Appointment.patient_id == user.id).order_by(models.Appointment.appointment_date.asc()).all()
    next_apt = appointments[0].appointment_date.isoformat() if appointments else "Not scheduled"
    
    return {
        "patient_id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "age": user.age if user.age else "Not specified",
        "blood_group": user.blood_group if user.blood_group else "Unknown",
        "latest_diagnosis": user.condition if user.condition else "None recorded",
        "allergies": [user.allergies] if user.allergies else ["None recorded"],
        "prescriptions": prescriptions if prescriptions else [],
        "recent_vitals": vitals_data,
        "last_visit": "2024-03-01",
        "next_appointment": next_apt
    }

# --- Vitals ---

@app.post("/api/vitals", response_model=schemas.VitalResponse)
def submit_vital(vital: schemas.VitalCreate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_vital = models.Vital(**vital.model_dump(), patient_id=current_user.id)
    db.add(db_vital)
    db.commit()
    db.refresh(db_vital)
    return db_vital

@app.get("/api/vitals/{patient_id}", response_model=List[schemas.VitalResponse])
def get_vitals(patient_id: int, db: Session = Depends(database.get_db)):
    return db.query(models.Vital).filter(models.Vital.patient_id == patient_id).order_by(models.Vital.recorded_at.desc()).all()

# --- Appointments ---

@app.post("/api/appointments", response_model=schemas.AppointmentResponse)
def create_appointment(appointment: schemas.AppointmentCreate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    # Assuming the current user (could be doctor or patient) creates the appointment
    appt_data = appointment.model_dump()
    
    # Fill in the ID for the creator
    if current_user.role == "patient":
        appt_data["patient_id"] = current_user.id
    elif current_user.role == "doctor":
        appt_data["doctor_id"] = current_user.id
        
    db_appointment = models.Appointment(**appt_data)
    db.add(db_appointment)
    db.commit()
    db.refresh(db_appointment)
    return db_appointment

@app.get("/api/appointments/{user_id}", response_model=List[schemas.AppointmentResponse])
def get_appointments(user_id: int, db: Session = Depends(database.get_db)):
    # Returns appointments for user whether they are doctor or patient
    return db.query(models.Appointment).filter(
        (models.Appointment.patient_id == user_id) | (models.Appointment.doctor_id == user_id)
    ).all()

# --- Messages ---

@app.post("/api/messages", response_model=schemas.MessageResponse)
def send_message(message: schemas.MessageCreate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_message = models.Message(**message.model_dump(), sender_id=current_user.id)
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

@app.get("/api/messages/{other_user_id}", response_model=List[schemas.MessageResponse])
def get_messages(other_user_id: int, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.Message).filter(
        ((models.Message.sender_id == current_user.id) & (models.Message.receiver_id == other_user_id)) |
        ((models.Message.sender_id == other_user_id) & (models.Message.receiver_id == current_user.id))
    ).order_by(models.Message.sent_at.asc()).all()

# --- Patient-Doctor Linking ---

@app.post("/api/links", response_model=schemas.PatientDoctorLinkResponse)
def request_doctor_link(link_request: schemas.PatientDoctorLinkCreate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Only patients can request links")
    
    # Check if a link already exists
    existing = db.query(models.PatientDoctorLink).filter(
        models.PatientDoctorLink.patient_id == current_user.id,
        models.PatientDoctorLink.doctor_id == link_request.doctor_id
    ).first()
    
    if existing:
        return existing
        
    db_link = models.PatientDoctorLink(patient_id=current_user.id, doctor_id=link_request.doctor_id)
    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    return db_link

@app.get("/api/links/doctor")
def get_doctor_links(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can view these requests")
        
    links = db.query(models.PatientDoctorLink).filter(models.PatientDoctorLink.doctor_id == current_user.id).all()
    result = []
    for link in links:
        patient = db.query(models.User).filter(models.User.id == link.patient_id).first()
        result.append({
            "id": link.id,
            "patient_id": link.patient_id,
            "patient_name": patient.name if patient else "Unknown",
            "status": link.status,
            "created_at": link.created_at.isoformat()
        })
    return result

@app.put("/api/links/{link_id}/status")
def update_link_status(link_id: int, status: str, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can update requested links")
        
    db_link = db.query(models.PatientDoctorLink).filter(models.PatientDoctorLink.id == link_id, models.PatientDoctorLink.doctor_id == current_user.id).first()
    if not db_link:
        raise HTTPException(status_code=404, detail="Link request not found")
        
    db_link.status = status
    db.commit()
    return {"detail": f"Request {status}"}

@app.get("/api/links/patient/current")
def get_current_doctor(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Only patients can view their doctor")
        
    link = db.query(models.PatientDoctorLink).filter(
        models.PatientDoctorLink.patient_id == current_user.id,
        models.PatientDoctorLink.status == "accepted"
    ).first()
    
    if not link:
        return {"assigned": False}
        
    doctor = db.query(models.User).filter(models.User.id == link.doctor_id).first()
    return {
        "assigned": True,
        "doctor_id": doctor.id,
        "doctor_name": doctor.name,
        "hospital": "Careloop Network" # Mock property
    }

# --- AI & Alerts ---

@app.post("/api/ai/chat", response_model=schemas.AIResponse)
def ai_chat(prompt_data: schemas.AIPrompt, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    user_condition = current_user.condition or "No specific condition recorded."
    
    if not bedrock_runtime:
        return schemas.AIResponse(
            response="AI Service is currently unavailable. Please try again later.",
            is_critical=False
        )

    system_prompt = (
        f"You are CareLoop AI, a professional medical assistant. "
        f"The patient's diagnosed condition is: {user_condition}. "
        f"Rules: "
        f"1. If the symptom is RELATED to their condition, provide helpful advice. "
        f"2. If the symptom is NOT RELATED to their condition and potentially serious, say: "
        f"'This seems unrelated to your current condition. Would you like me to send a critical alert to your doctor?' "
        f"3. Set is_critical to true ONLY if the issue is unrelated and potentially serious. "
        f"Always reply in plain helpful text. Do NOT wrap your answer in JSON."
    )

    full_message = f"{system_prompt}\n\nPatient says: {prompt_data.prompt}"

    try:
        body = json.dumps({
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": full_message}]
                }
            ]
        })

        response = bedrock_runtime.invoke_model(
            modelId="amazon.nova-micro-v1:0",
            body=body,
            contentType="application/json",
            accept="application/json"
        )

        result = json.loads(response["body"].read())
        # Nova Micro response format: result["output"]["message"]["content"][0]["text"]
        content = result["output"]["message"]["content"][0]["text"]

        # Determine if this is a critical alert based on AI response
        is_critical = "send a critical alert" in content.lower() or "unrelated to your current condition" in content.lower()

        return schemas.AIResponse(response=content, is_critical=is_critical)

    except Exception as e:
        print(f"AI Chat Error: {e}")
        return schemas.AIResponse(response=f"I encountered an error processing your request: {str(e)}", is_critical=False)

@app.post("/api/alerts", response_model=schemas.AlertResponse)
def create_alert(alert: schemas.AlertCreate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_alert = models.Alert(**alert.model_dump(), patient_id=current_user.id)
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert

@app.get("/api/alerts/doctor", response_model=List[schemas.AlertResponse])
def get_doctor_alerts(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can view alerts")
    return db.query(models.Alert).filter(models.Alert.doctor_id == current_user.id).order_by(models.Alert.created_at.desc()).all()

@app.put("/api/alerts/{alert_id}/read")
def mark_alert_read(alert_id: int, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_alert = db.query(models.Alert).filter(models.Alert.id == alert_id, models.Alert.doctor_id == current_user.id).first()
    if not db_alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    db_alert.is_read = True
    db.commit()
    return {"detail": "Alert marked as read"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="192.168.1.3", port=8000, reload=True)

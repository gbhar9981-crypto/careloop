from pydantic import BaseModel
from typing import Optional, List
import datetime

class UserBase(BaseModel):
    email: str
    name: str
    role: Optional[str] = "patient"

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[str] = None
    blood_group: Optional[str] = None
    condition: Optional[str] = None
    allergies: Optional[str] = None

class UserResponse(UserBase):
    id: int
    is_active: bool
    age: Optional[str] = None
    blood_group: Optional[str] = None
    condition: Optional[str] = None
    allergies: Optional[str] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class TokenData(BaseModel):
    email: Optional[str] = None

class MedicineBase(BaseModel):
    name: str
    dosage: str
    time_to_take: str

class MedicineCreate(MedicineBase):
    pass

class MedicineResponse(MedicineBase):
    id: int
    user_id: int
    is_taken: bool = False

    class Config:
        from_attributes = True

class ReviewBase(BaseModel):
    rating: int
    problem: Optional[str] = None

class ReviewCreate(ReviewBase):
    pass

class ReviewResponse(ReviewBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True

class DoctorResponse(BaseModel):
    id: int
    name: str
    specialty: str
    hospital: str
    rating: float

class ConditionResponse(BaseModel):
    id: int
    name: str
    description: str
    symptoms: List[str]

class HospitalResponse(BaseModel):
    id: int
    name: str
    address: str
    lat: float
    lng: float

class VitalBase(BaseModel):
    bp: str
    pulse: int
    oxygen: int
    temperature: float

class VitalCreate(VitalBase):
    pass

class VitalResponse(VitalBase):
    id: int
    patient_id: int
    recorded_at: datetime.datetime

    class Config:
        from_attributes = True

class ReportBase(BaseModel):
    report_type: str
    file_url: str

class ReportCreate(ReportBase):
    pass

class ReportResponse(ReportBase):
    id: int
    patient_id: int
    uploaded_at: datetime.datetime

    class Config:
        from_attributes = True

class AppointmentBase(BaseModel):
    doctor_id: Optional[int] = None
    patient_id: Optional[int] = None
    appointment_date: datetime.datetime
    appointment_type: str

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentResponse(AppointmentBase):
    id: int

    class Config:
        from_attributes = True

class MessageBase(BaseModel):
    receiver_id: int
    content: str

class MessageCreate(MessageBase):
    pass

class MessageResponse(MessageBase):
    id: int
    sender_id: int
    receiver_id: int
    content: str
    sent_at: datetime.datetime

    class Config:
        from_attributes = True

class PatientDoctorLinkCreate(BaseModel):
    doctor_id: int

class PatientDoctorLinkResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    status: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class AIPrompt(BaseModel):
    prompt: str

class AIResponse(BaseModel):
    response: str
    is_critical: bool

class AlertBase(BaseModel):
    doctor_id: int
    message: str

class AlertCreate(AlertBase):
    pass

class AlertResponse(AlertBase):
    id: int
    patient_id: int
    is_read: bool
    created_at: datetime.datetime

    class Config:
        from_attributes = True

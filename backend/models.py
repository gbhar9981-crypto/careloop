from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, DateTime, Text
from sqlalchemy.orm import relationship
import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255))
    name = Column(String(255))
    is_active = Column(Boolean, default=True)
    role = Column(String(50), default="patient") # "patient" or "doctor"
    
    # New patient info fields
    age = Column(String(50), nullable=True)
    blood_group = Column(String(20), nullable=True)
    condition = Column(Text, nullable=True)
    allergies = Column(Text, nullable=True)
    
    medicines = relationship("Medicine", back_populates="owner")
    reviews = relationship("Review", back_populates="owner")
    vitals = relationship("Vital", back_populates="patient", foreign_keys="Vital.patient_id")
    reports = relationship("Report", back_populates="patient", foreign_keys="Report.patient_id")
    appointments_as_patient = relationship("Appointment", back_populates="patient", foreign_keys="Appointment.patient_id")
    appointments_as_doctor = relationship("Appointment", back_populates="doctor", foreign_keys="Appointment.doctor_id")
    messages_sent = relationship("Message", back_populates="sender", foreign_keys="Message.sender_id")
    messages_received = relationship("Message", back_populates="receiver", foreign_keys="Message.receiver_id")
    alerts_received = relationship("Alert", back_populates="doctor", foreign_keys="Alert.doctor_id")
    alerts_sent = relationship("Alert", back_populates="patient", foreign_keys="Alert.patient_id")

class Medicine(Base):
    __tablename__ = "medicines"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    dosage = Column(String(255))
    time_to_take = Column(String(50)) # H:M format
    user_id = Column(Integer, ForeignKey("users.id"))
    is_taken = Column(Boolean, default=False)
    
    owner = relationship("User", back_populates="medicines")

class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    rating = Column(Integer)
    problem = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    owner = relationship("User", back_populates="reviews")

class Vital(Base):
    __tablename__ = "vitals"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"))
    bp = Column(String(50))
    pulse = Column(Integer)
    oxygen = Column(Integer)
    temperature = Column(Float)
    recorded_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    patient = relationship("User", back_populates="vitals", foreign_keys=[patient_id])

class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"))
    report_type = Column(String(100))
    file_url = Column(String(500)) # Can be a local path or cloud URL
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    patient = relationship("User", back_populates="reports", foreign_keys=[patient_id])

class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"))
    patient_id = Column(Integer, ForeignKey("users.id"))
    appointment_date = Column(DateTime)
    appointment_type = Column(String(100)) # e.g. "Video Call", "In Person"
    
    doctor = relationship("User", back_populates="appointments_as_doctor", foreign_keys=[doctor_id])
    patient = relationship("User", back_populates="appointments_as_patient", foreign_keys=[patient_id])

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    sent_at = Column(DateTime, default=datetime.datetime.utcnow)
    sender = relationship("User", back_populates="messages_sent", foreign_keys=[sender_id])
    receiver = relationship("User", back_populates="messages_received", foreign_keys=[receiver_id])

class PatientDoctorLink(Base):
    __tablename__ = "patient_doctor_links"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"))
    doctor_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String(50), default="pending") # "pending", "accepted", "rejected"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    patient = relationship("User", foreign_keys=[patient_id])
    doctor = relationship("User", foreign_keys=[doctor_id])

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"))
    doctor_id = Column(Integer, ForeignKey("users.id"))
    message = Column(Text)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    patient = relationship("User", back_populates="alerts_sent", foreign_keys=[patient_id])
    doctor = relationship("User", back_populates="alerts_received", foreign_keys=[doctor_id])

"""
Database models for the Slide Generator application.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from database import Base

class ProjectStatus(enum.Enum):
    """Status of a project."""
    DRAFT = "draft"
    GENERATING_SCRIPT = "generating_script"
    SCRIPT_READY = "script_ready"
    GENERATING_SLIDES = "generating_slides"
    SLIDES_READY = "slides_ready"
    GENERATING_VIDEO = "generating_video"
    COMPLETED = "completed"
    FAILED = "failed"

class AssetType(enum.Enum):
    """Types of generated assets."""
    SCRIPT_PDF = "script_pdf"
    SLIDES_PDF = "slides_pdf"
    VIDEO = "video"
    JSON_SCRIPT = "json_script"

class Project(Base):
    """
    Represents a slide generation project.
    """
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    outline = Column(String, nullable=True)  # The original user input
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.DRAFT)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship: One project can have many assets
    assets = relationship("Asset", back_populates="project", cascade="all, delete-orphan")

class Asset(Base):
    """
    Represents a generated file (PDF, video, JSON, etc.).
    """
    __tablename__ = "assets"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    asset_type = Column(SQLEnum(AssetType), nullable=False)
    file_path = Column(String, nullable=False)  # Path to the file on disk (or S3 URL in future)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship: Each asset belongs to one project
    project = relationship("Project", back_populates="assets")

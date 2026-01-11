import os
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from pathlib import Path
import json

# Setup database path
PROJECT_ROOT = Path(__file__).parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "script_generator.db"
DB_PATH.parent.mkdir(exist_ok=True)

# SQLAlchemy boilerplate
Base = declarative_base()
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Project(Base):
    """Stores the global metadata for a script."""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    source_language = Column(String, default="en")
    metadata_json = Column(Text, nullable=True) # For additional script info
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    slides = relationship("Slide", back_populates="project", cascade="all, delete-orphan")

class Slide(Base):
    """Stores the base content for each row (slide)."""
    __tablename__ = "slides"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    slide_number = Column(Integer, nullable=False)
    original_narration = Column(Text, nullable=True)
    original_visual_cue = Column(Text, nullable=True)
    
    project = relationship("Project", back_populates="slides")
    translations = relationship("Translation", back_populates="slide", cascade="all, delete-orphan")

class Translation(Base):
    """Stores a single grid cell (translation for a specific language)."""
    __tablename__ = "translations"
    
    id = Column(Integer, primary_key=True, index=True)
    slide_id = Column(Integer, ForeignKey("slides.id"))
    language_code = Column(String, nullable=False) # 'hi', 'ta', etc.
    language_name = Column(String, nullable=False) # 'Hindi', 'Tamil', etc.
    translated_narration = Column(Text, nullable=True)
    translated_visual_cue = Column(Text, nullable=True)
    audio_url = Column(String, nullable=True)
    is_edited = Column(Boolean, default=False)
    is_audio_stale = Column(Boolean, default=False)
    
    slide = relationship("Slide", back_populates="translations")

# Initialize database
def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def save_project_results(json_script: dict, results: list):
    """
    Saves a project, its slides, and all language translations to the DB.
    """
    db = SessionLocal()
    try:
        # 1. Create or Find Project
        title = json_script.get("presentation_title", "Untitled Project")
        project = Project(
            title=title,
            metadata_json=json.dumps({
                k: v for k, v in json_script.items() 
                if k not in ["slides"]
            })
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        
        # 2. Create Slides
        slides_map = {} # Maps slide_number to Slide object
        for i, slide_data in enumerate(json_script.get("slides", []), 1):
            # Fallback to the loop index if slide_number is missing
            slide_num = slide_data.get("slide_number") or i
            
            slide = Slide(
                project_id=project.id,
                slide_number=slide_num,
                original_narration=slide_data.get("narration"),
                original_visual_cue=slide_data.get("visual_cue") or slide_data.get("image_prompt")
            )
            db.add(slide)
            slides_map[slide_num] = slide
        
        db.commit()
        
        # 3. Create Translations
        for res in results:
            if not res.success:
                continue
                
            lang_code = res.language_code
            lang_name = res.language
            
            translated_slides = res.translated_script.get("slides", [])
            for j, ts in enumerate(translated_slides, 1):
                # Match by slide_number or index
                slide_num = ts.get("slide_number") or j
                if slide_num in slides_map:
                    translation = Translation(
                        slide_id=slides_map[slide_num].id,
                        language_code=lang_code,
                        language_name=lang_name,
                        translated_narration=ts.get(f"narration_{lang_code}"),
                        translated_visual_cue=ts.get(f"visual_cue_{lang_code}")
                    )
                    db.add(translation)
        
        db.commit()
        return project.id
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error saving to database: {e}")
        raise e
    finally:
        db.close()

def update_translation_cell(slide_id: int, language_code: str, text: str = None, visual_cue: str = None):
    """Updates a specific translation cell in the DB."""
    db = SessionLocal()
    try:
        translation = db.query(Translation).filter(
            Translation.slide_id == slide_id,
            Translation.language_code == language_code
        ).first()
        
        if translation:
            if text is not None:
                if translation.translated_narration != text:
                    translation.translated_narration = text
                    translation.is_edited = True
                    translation.is_audio_stale = True
            
            if visual_cue is not None:
                if translation.translated_visual_cue != visual_cue:
                    translation.translated_visual_cue = visual_cue
                    translation.is_edited = True
            
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def get_project_grid_data(project_id: int):
    """Retrieves all data for a project in a flat grid format."""
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return None
            
        grid_data = []
        for slide in project.slides:
            row = {
                "slide_id": slide.id,
                "slide_number": slide.slide_number,
                "english": slide.original_narration,
                "visual_cue": slide.original_visual_cue,
                "translations": {}
            }
            for trans in slide.translations:
                row["translations"][trans.language_code] = {
                    "text": trans.translated_narration,
                    "visual_cue": trans.translated_visual_cue,
                    "audio_url": trans.audio_url,
                    "is_edited": trans.is_edited,
                    "is_audio_stale": trans.is_audio_stale
                }
            grid_data.append(row)
            
        return {
            "project_id": project.id,
            "title": project.title,
            "grid": grid_data
        }
    finally:
        db.close()

def get_translation_by_id(translation_id: int):
    """Get a specific translation row by its ID."""
    db = SessionLocal()
    try:
        translation = db.query(Translation).filter(Translation.id == translation_id).first()
        if not translation:
            return None
        return {
            "id": translation.id,
            "slide_id": translation.slide_id,
            "language_code": translation.language_code,
            "text": translation.translated_narration,
            "audio_url": translation.audio_url
        }
    finally:
        db.close()

def update_translation_audio(translation_id: int, audio_url: str):
    """Update the audio URL for a translation and mark audio as fresh."""
    db = SessionLocal()
    try:
        translation = db.query(Translation).filter(Translation.id == translation_id).first()
        if translation:
            translation.audio_url = audio_url
            translation.is_audio_stale = False
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

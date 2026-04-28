"""
Projektkontextverwaltung
Dient zur Persistenz des Projektstatus auf dem Server, um keine großen Datenmengen zwischen Frontend-Schnittstellen übertragen zu müssen
"""

import os
import json
import uuid
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass, field, asdict
from ..config import Config


class ProjectStatus(str, Enum):
    """Projektstatus"""
    CREATED = "created"              # Gerade erstellt, Dateien hochgeladen
    ONTOLOGY_GENERATED = "ontology_generated"  #Ontologie erstellt
    GRAPH_BUILDING = "graph_building"    # Graph wird erstellt
    GRAPH_COMPLETED = "graph_completed"  # Graph erstellt
    FAILED = "failed"                # Fehlgeschlagen


@dataclass
class Project:
    """Projekt-Datenmodell"""
    project_id: str
    name: str
    status: ProjectStatus
    created_at: str
    updated_at: str
    
    # Dateiinformationen
    files: List[Dict[str, str]] = field(default_factory=list)  # [{filename, path, size}]
    total_text_length: int = 0
    
    #Ontologieinformationen (nach Schnittstelle 1 ausfüllen)
    ontology: Optional[Dict[str, Any]] = None
    analysis_summary: Optional[str] = None
    
    # Graph-Informationen (nach Schnittstelle 2 ausfüllen)
    graph_id: Optional[str] = None
    graph_build_task_id: Optional[str] = None
    
    # Konfiguration
    simulation_requirement: Optional[str] = None
    chunk_size: int = 500
    chunk_overlap: int = 50
    
    # Fehlerinformationen
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """In Dictionary konvertieren"""
        return {
            "project_id": self.project_id,
            "name": self.name,
            "status": self.status.value if isinstance(self.status, ProjectStatus) else self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "files": self.files,
            "total_text_length": self.total_text_length,
            "ontology": self.ontology,
            "analysis_summary": self.analysis_summary,
            "graph_id": self.graph_id,
            "graph_build_task_id": self.graph_build_task_id,
            "simulation_requirement": self.simulation_requirement,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "error": self.error
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        """Aus Dictionary erstellen"""
        status = data.get('status', 'created')
        if isinstance(status, str):
            status = ProjectStatus(status)
        
        # JSON-Strings parsen falls vorhanden
        ontology = data.get('ontology')
        if isinstance(ontology, str):
            try:
                ontology = json.loads(ontology)
            except:
                pass
                
        files = data.get('files', [])
        if isinstance(files, str):
            try:
                files = json.loads(files)
            except:
                files = []
        
        return cls(
            project_id=data['project_id'],
            name=data.get('name', 'Unnamed Project'),
            status=status,
            created_at=data.get('created_at', ''),
            updated_at=data.get('updated_at', ''),
            files=files,
            total_text_length=data.get('total_text_length', 0),
            ontology=ontology,
            analysis_summary=data.get('analysis_summary'),
            graph_id=data.get('graph_id'),
            graph_build_task_id=data.get('graph_build_task_id'),
            simulation_requirement=data.get('simulation_requirement'),
            chunk_size=data.get('chunk_size', 500),
            chunk_overlap=data.get('chunk_overlap', 50),
            error=data.get('error')
        )


import sqlite3
from flask import g


class ProjectManager:
    """Projektmanager - Verantwortlich für persistente Speicherung und Abruf von Projekten in SQLite (per Tenant)"""
    
    @classmethod
    def _get_conn(cls):
        """Erstellt eine SQLite-Verbindung für den aktuellen Tenant"""
        if not g.tenant:
            raise RuntimeError("Kein Tenant im Kontext gefunden.")
        
        # Datenbankdatei im Tenant-Verzeichnis ablegen
        db_path = os.path.join(cls._get_tenant_upload_dir(), 'data.db')
        
        # Verbindung herstellen
        conn = sqlite3.connect(db_path)
        # Ermöglicht Zugriff auf Spalten per Name: row['column_name']
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def _ensure_tenant_schema(cls, conn):
        """Stellt sicher, dass die Projekttabelle in der SQLite-Datei existiert"""
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                project_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                metadata TEXT DEFAULT '{}',
                ontology TEXT,
                analysis_summary TEXT,
                graph_id TEXT,
                graph_build_task_id TEXT,
                simulation_requirement TEXT,
                chunk_size INTEGER DEFAULT 500,
                chunk_overlap INTEGER DEFAULT 50,
                error TEXT,
                files TEXT DEFAULT '[]'
            )
        """)
        conn.commit()

    @classmethod
    def _get_tenant_upload_dir(cls) -> str:
        """Stammverzeichnis für Projektspeicher des aktuellen Tenants abrufen"""
        tenant_id = g.tenant.tenant_id if g.tenant else 'default'
        # Pfad: uploads/tenants/{tenant_id}/
        path = os.path.join(Config.UPLOAD_FOLDER, 'tenants', tenant_id)
        os.makedirs(path, exist_ok=True)
        return path

    @classmethod
    def create_project(cls, name: str = "Unnamed Project") -> Project:
        """Neues Projekt in der SQLite-DB des Tenants erstellen"""
        project_id = f"proj_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()
        
        project = Project(
            project_id=project_id,
            name=name,
            status=ProjectStatus.CREATED,
            created_at=now,
            updated_at=now
        )
        
        conn = cls._get_conn()
        try:
            cls._ensure_tenant_schema(conn)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO projects (project_id, name, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (project.project_id, project.name, project.status.value, now, now))
            conn.commit()
        finally:
            conn.close()
            
        # Projektverzeichnis für Dateien erstellen
        os.makedirs(os.path.join(cls._get_tenant_upload_dir(), 'projects', project_id), exist_ok=True)
        
        return project

    @classmethod
    def save_project(cls, project: Project) -> None:
        """Projekt-Metadaten in der SQLite-DB aktualisieren"""
        now = datetime.now().isoformat()
        project.updated_at = now
        
        conn = cls._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE projects SET
                    name = ?,
                    status = ?,
                    updated_at = ?,
                    metadata = ?,
                    ontology = ?,
                    analysis_summary = ?,
                    graph_id = ?,
                    graph_build_task_id = ?,
                    simulation_requirement = ?,
                    chunk_size = ?,
                    chunk_overlap = ?,
                    error = ?,
                    files = ?
                WHERE project_id = ?
            """, (
                project.name, 
                project.status.value if isinstance(project.status, ProjectStatus) else project.status,
                now,
                json.dumps({}), # placeholder für metadata
                json.dumps(project.ontology) if project.ontology else None,
                project.analysis_summary,
                project.graph_id,
                project.graph_build_task_id,
                project.simulation_requirement,
                project.chunk_size,
                project.chunk_overlap,
                project.error,
                json.dumps(project.files),
                project.project_id
            ))
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def get_project(cls, project_id: str) -> Optional[Project]:
        """Projekt aus der SQLite-DB abrufen"""
        conn = cls._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            # Row-Objekt in Dictionary konvertieren
            data = dict(row)
            return Project.from_dict(data)
        finally:
            conn.close()

    @classmethod
    def list_projects(cls, limit: int = 50) -> List[Project]:
        """Alle Projekte des Tenants auflisten"""
        projects = []
        try:
            conn = cls._get_conn()
            cls._ensure_tenant_schema(conn)
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM projects 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (limit,))
                for row in cursor.fetchall():
                    projects.append(Project.from_dict(dict(row)))
            finally:
                conn.close()
        except Exception as e:
            print(f"Error listing projects: {e}")
            return []
            
        return projects

    @classmethod
    def delete_project(cls, project_id: str) -> bool:
        """Projekt aus SQLite-DB und Dateisystem löschen"""
        conn = cls._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM projects WHERE project_id = ?", (project_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
        finally:
            conn.close()
            
        if deleted:
            project_dir = os.path.join(cls._get_tenant_upload_dir(), 'projects', project_id)
            if os.path.exists(project_dir):
                shutil.rmtree(project_dir)
            return True
        return False

    @classmethod
    def save_file_to_project(cls, project_id: str, file_storage, original_filename: str) -> Dict[str, str]:
        """Datei im Tenant-spezifischen Ordner speichern"""
        project_dir = os.path.join(cls._get_tenant_upload_dir(), 'projects', project_id)
        files_dir = os.path.join(project_dir, 'files')
        os.makedirs(files_dir, exist_ok=True)
        
        ext = os.path.splitext(original_filename)[1].lower()
        safe_filename = f"{uuid.uuid4().hex[:8]}{ext}"
        file_path = os.path.join(files_dir, safe_filename)
        
        file_storage.save(file_path)
        file_size = os.path.getsize(file_path)
        
        return {
            "original_filename": original_filename,
            "saved_filename": safe_filename,
            "path": file_path,
            "size": file_size
        }

    @classmethod
    def save_extracted_text(cls, project_id: str, text: str) -> None:
        """Extrahierten Text in Datei speichern"""
        text_path = os.path.join(cls._get_tenant_upload_dir(), 'projects', project_id, 'extracted_text.txt')
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(text)

    @classmethod
    def get_extracted_text(cls, project_id: str) -> Optional[str]:
        text_path = os.path.join(cls._get_tenant_upload_dir(), 'projects', project_id, 'extracted_text.txt')
        if not os.path.exists(text_path):
            return None
        with open(text_path, 'r', encoding='utf-8') as f:
            return f.read()

    @classmethod
    def get_project_files(cls, project_id: str) -> List[str]:
        files_dir = os.path.join(cls._get_tenant_upload_dir(), 'projects', project_id, 'files')
        if not os.path.exists(files_dir):
            return []
        return [
            os.path.join(files_dir, f) 
            for f in os.listdir(files_dir) 
            if os.path.isfile(os.path.join(files_dir, f))
        ]


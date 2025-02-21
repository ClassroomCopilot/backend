from fastapi import APIRouter, Request, Depends, HTTPException, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Dict
import os
from modules.logger_tool import initialise_logger
from modules.database.services.admin_service import AdminService, AdminProfileBase
from modules.database.services.school_admin_service import SchoolAdminService
from modules.database.supabase.utils.storage import StorageManager
from .auth import verify_admin
import csv
import io

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("LOG_PATH"), 'default', True)

# Initialize services
admin_service = AdminService()
school_service = SchoolAdminService()
storage_manager = StorageManager()

@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, admin: Dict = Depends(verify_admin)):
    """Render admin dashboard"""
    return templates.TemplateResponse(
        "admin/dashboard/index.html",
        {
            "request": request, 
            "admin": admin,
            "app_version": os.getenv("APP_VERSION", "Unknown")
        }
    )

@router.get("/users")
async def list_users(request: Request, admin: Dict = Depends(verify_admin)):
    """List all users"""
    return templates.TemplateResponse(
        "admin/users/list.html",
        {"request": request, "admin": admin}
    )

@router.get("/users/{user_id}")
async def get_user(request: Request, user_id: str, admin: Dict = Depends(verify_admin)):
    """Get user details"""
    return templates.TemplateResponse(
        "admin/users/detail.html",
        {"request": request, "admin": admin, "user_id": user_id}
    )

@router.get("/admins")
async def list_admins(request: Request, admin: Dict = Depends(verify_admin)):
    """List all admins"""
    if not admin.get("is_super_admin"):
        raise HTTPException(status_code=403, detail="Only super admins can view admin list")
    
    admins = admin_service.list_admins()
    return templates.TemplateResponse(
        "admin/users/admins.html",
        {"request": request, "admin": admin, "admins": admins}
    )

@router.post("/admins")
async def create_admin(admin_data: AdminProfileBase, current_admin: Dict = Depends(verify_admin)):
    """Create a new admin"""
    try:
        result = admin_service.create_admin(admin_data, current_admin)
        return JSONResponse(content={"status": "success", "admin": result})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/schools/manage", response_class=HTMLResponse)
async def manage_schools(request: Request, admin: Dict = Depends(verify_admin)):
    """Manage schools page"""
    try:
        # Fetch schools from Supabase
        result = admin_service.supabase.table("schools").select("*").execute()
        schools = result.data if result else []
        
        # Sort schools by establishment_name
        schools.sort(key=lambda x: x.get("establishment_name", ""))
        
        return templates.TemplateResponse(
            "admin/schools/manage.html",
            {
                "request": request, 
                "admin": admin,
                "schools": schools,
                "schools_count": len(schools)
            }
        )
    except Exception as e:
        logger.error(f"Error fetching schools: {str(e)}")
        return templates.TemplateResponse(
            "admin/schools/manage.html",
            {
                "request": request,
                "admin": admin,
                "schools": [],
                "schools_count": 0,
                "error": str(e)
            }
        )

@router.post("/schools/import")
async def import_schools(
    file: UploadFile = File(...),
    admin: Dict = Depends(verify_admin)
):
    """Import schools from CSV file"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Please upload a CSV file")
    
    try:
        # Process the CSV file
        content = await file.read()
        csv_text = content.decode('utf-8-sig')  # Handle BOM if present
        csv_reader = csv.DictReader(io.StringIO(csv_text))
        
        # Prepare data for batch insert
        schools_data = []
        for row in csv_reader:
            school_data = {
                "urn": row.get("URN"),
                "la_code": row.get("LA (code)"),
                "la_name": row.get("LA (name)"),
                "establishment_number": row.get("EstablishmentNumber"),
                "establishment_name": row.get("EstablishmentName"),
                "establishment_type": row.get("TypeOfEstablishment (name)"),
                "establishment_type_group": row.get("EstablishmentTypeGroup (name)"),
                "establishment_status": row.get("EstablishmentStatus (name)"),
                "reason_establishment_opened": row.get("ReasonEstablishmentOpened (name)"),
                "open_date": row.get("OpenDate"),
                "reason_establishment_closed": row.get("ReasonEstablishmentClosed (name)"),
                "close_date": row.get("CloseDate"),
                "phase_of_education": row.get("PhaseOfEducation (name)"),
                "statutory_low_age": row.get("StatutoryLowAge"),
                "statutory_high_age": row.get("StatutoryHighAge"),
                "boarders": row.get("Boarders (name)"),
                "nursery_provision": row.get("NurseryProvision (name)"),
                "official_sixth_form": row.get("OfficialSixthForm (name)"),
                "gender": row.get("Gender (name)"),
                "religious_character": row.get("ReligiousCharacter (name)"),
                "religious_ethos": row.get("ReligiousEthos (name)"),
                "diocese": row.get("Diocese (name)"),
                "admissions_policy": row.get("AdmissionsPolicy (name)"),
                "school_capacity": row.get("SchoolCapacity"),
                "special_classes": row.get("SpecialClasses (name)"),
                "census_date": row.get("CensusDate"),
                "number_of_pupils": row.get("NumberOfPupils"),
                "number_of_boys": row.get("NumberOfBoys"),
                "number_of_girls": row.get("NumberOfGirls"),
                "percentage_fsm": row.get("PercentageFSM"),
                "trust_school_flag": row.get("TrustSchoolFlag (name)"),
                "trusts_name": row.get("Trusts (name)"),
                "school_sponsor_flag": row.get("SchoolSponsorFlag (name)"),
                "school_sponsors_name": row.get("SchoolSponsors (name)"),
                "federation_flag": row.get("FederationFlag (name)"),
                "federations_name": row.get("Federations (name)"),
                "ukprn": row.get("UKPRN"),
                "fehe_identifier": row.get("FEHEIdentifier"),
                "further_education_type": row.get("FurtherEducationType (name)"),
                "ofsted_last_inspection": row.get("OfstedLastInsp"),
                "last_changed_date": row.get("LastChangedDate"),
                "street": row.get("Street"),
                "locality": row.get("Locality"),
                "address3": row.get("Address3"),
                "town": row.get("Town"),
                "county": row.get("County (name)"),
                "postcode": row.get("Postcode"),
                "school_website": row.get("SchoolWebsite"),
                "telephone_num": row.get("TelephoneNum"),
                "head_title": row.get("HeadTitle (name)"),
                "head_first_name": row.get("HeadFirstName"),
                "head_last_name": row.get("HeadLastName"),
                "head_preferred_job_title": row.get("HeadPreferredJobTitle"),
                "gssla_code": row.get("GSSLACode (name)"),
                "parliamentary_constituency": row.get("ParliamentaryConstituency (name)"),
                "urban_rural": row.get("UrbanRural (name)"),
                "rsc_region": row.get("RSCRegion (name)"),
                "country": row.get("Country (name)"),
                "uprn": row.get("UPRN"),
                "sen_stat": row.get("SENStat") == "true",
                "sen_no_stat": row.get("SENNoStat") == "true",
                "sen_unit_on_roll": row.get("SenUnitOnRoll"),
                "sen_unit_capacity": row.get("SenUnitCapacity"),
                "resourced_provision_on_roll": row.get("ResourcedProvisionOnRoll"),
                "resourced_provision_capacity": row.get("ResourcedProvisionCapacity"),
            }
            
            # Clean up empty strings and convert types
            for key, value in school_data.items():
                if value == "":
                    school_data[key] = None
                elif key in ["statutory_low_age", "statutory_high_age", "school_capacity", 
                           "number_of_pupils", "number_of_boys", "number_of_girls",
                           "sen_unit_on_roll", "sen_unit_capacity",
                           "resourced_provision_on_roll", "resourced_provision_capacity"]:
                    if value:
                        try:
                            float_val = float(value)
                            int_val = int(float_val)
                            school_data[key] = int_val
                        except (ValueError, TypeError):
                            school_data[key] = None
                elif key == "percentage_fsm":
                    if value:
                        try:
                            school_data[key] = float(value)
                        except (ValueError, TypeError):
                            school_data[key] = None
                elif key in ["open_date", "close_date", "census_date", 
                           "ofsted_last_inspection", "last_changed_date"]:
                    if value:
                        try:
                            # Convert date from DD-MM-YYYY to YYYY-MM-DD
                            parts = value.split("-")
                            if len(parts) == 3:
                                school_data[key] = f"{parts[2]}-{parts[1]}-{parts[0]}"
                            else:
                                school_data[key] = None
                        except:
                            school_data[key] = None
            
            schools_data.append(school_data)
        
        # Batch insert schools using admin service's Supabase client
        if schools_data:
            result = admin_service.supabase.table("schools").upsert(
                schools_data, 
                on_conflict="urn"  # Update if URN already exists
            ).execute()
            
            logger.info(f"Imported {len(schools_data)} schools")
            return {"status": "success", "imported_count": len(schools_data)}
        else:
            raise HTTPException(status_code=400, detail="No valid school data found in CSV")
            
    except Exception as e:
        logger.error(f"Error importing schools: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/initialize-schools-database")
async def initialize_schools_database(admin: Dict = Depends(verify_admin)):
    """Initialize schools database"""
    if not admin.get("is_super_admin"):
        raise HTTPException(status_code=403, detail="Only super admins can initialize database")
    
    result = school_service.create_schools_database()
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@router.get("/check-schools-database")
async def check_schools_database(admin: Dict = Depends(verify_admin)):
    """Check schools database status"""
    try:
        # Use SchoolService to check if database exists and has required nodes/relationships
        result = school_service.check_schools_database()
        return {"exists": result["status"] == "success"}
    except Exception as e:
        logger.error(f"Error checking schools database: {str(e)}")
        return {"exists": False, "error": str(e)}

@router.get("/storage", response_class=HTMLResponse)
async def storage_management(request: Request, admin: Dict = Depends(verify_admin)):
    """Storage management page"""
    try:
        # Get list of storage buckets with correct IDs
        buckets = [
            {
                "id": "cc.ccschools",
                "name": "School Files",
                "public": False,
                "file_size_limit": 50 * 1024 * 1024,  # 50MB
                "allowed_mime_types": [
                    "image/*",
                    "video/*",
                    "application/pdf",
                    "application/msword",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "application/vnd.ms-excel",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "application/vnd.ms-powerpoint",
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    "text/plain",
                    "text/csv",
                    "application/json"
                ]
            },
            {
                "id": "cc.ccusers",
                "name": "User Files",
                "public": False,
                "file_size_limit": 50 * 1024 * 1024,  # 50MB
                "allowed_mime_types": [
                    "image/*",
                    "video/*",
                    "application/pdf",
                    "application/msword",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "application/vnd.ms-excel",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "application/vnd.ms-powerpoint",
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    "text/plain",
                    "text/csv",
                    "application/json"
                ]
            }
        ]
        
        return templates.TemplateResponse(
            "admin/storage/manage.html",
            {"request": request, "admin": admin, "buckets": buckets}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/storage/{bucket_id}/contents")
async def list_bucket_contents(
    request: Request,
    bucket_id: str,
    path: str = "",
    admin: Dict = Depends(verify_admin)
):
    """List contents of a storage bucket"""
    try:
        contents = storage_manager.list_bucket_contents(bucket_id, path)
        bucket = {"id": bucket_id, "name": bucket_id.replace("_", " ").title()}
        
        return templates.TemplateResponse(
            "admin/storage/contents.html",
            {
                "request": request,
                "admin": admin,
                "bucket": bucket,
                "contents": contents,
                "current_path": path
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/storage/{bucket_id}/download/{file_path:path}")
async def download_file(
    bucket_id: str,
    file_path: str,
    admin: Dict = Depends(verify_admin)
):
    """Get download URL for a file"""
    try:
        url = storage_manager.create_signed_url(bucket_id, file_path)
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/storage/{bucket_id}/objects/{object_path:path}")
async def delete_object(
    bucket_id: str,
    object_path: str,
    admin: Dict = Depends(verify_admin)
):
    """Delete an object from storage"""
    try:
        storage_manager.delete_file(bucket_id, object_path)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/check-storage")
async def check_storage(admin: Dict = Depends(verify_admin)):
    """Check storage buckets status"""
    try:
        # Use the same bucket IDs as defined in initialize_storage
        buckets = [
            {"id": "cc.ccusers", "name": "User Files"},
            {"id": "cc.ccschools", "name": "School Files"}
        ]
        
        results = []
        for bucket in buckets:
            exists = storage_manager.check_bucket_exists(bucket["id"])
            results.append({
                "id": bucket["id"],
                "name": bucket["name"],
                "exists": exists
            })
        
        return {"buckets": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/initialize-storage")
async def initialize_storage(admin: Dict = Depends(verify_admin)):
    """Initialize storage buckets and policies for schools"""
    try:
        # Verify super admin status
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can initialize storage")

        # Use the storage manager to initialize storage
        storage_manager = StorageManager()
        return storage_manager.initialize_storage()
    except Exception as e:
        logger.error(f"Error initializing storage: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/check-schema")
async def check_schema(admin: Dict = Depends(verify_admin)):
    """Check Neo4j schema status"""
    try:
        from modules.database.services.graph_service import GraphService
        graph_service = GraphService()
        
        # Get actual schema status
        schema_status = graph_service.check_schema_status()
        
        # Return status with proper validation
        return {
            "constraints_valid": schema_status["constraints_count"] > 0,
            "constraints_count": schema_status["constraints_count"],
            "indexes_valid": schema_status["indexes_count"] > 0,
            "indexes_count": schema_status["indexes_count"],
            "labels_valid": schema_status["labels_count"] > 0,
            "labels_count": schema_status["labels_count"]
        }
    except Exception as e:
        logger.error(f"Error checking schema: {str(e)}")
        return {
            "constraints_valid": False,
            "constraints_count": 0,
            "indexes_valid": False,
            "indexes_count": 0,
            "labels_valid": False,
            "labels_count": 0,
            "error": str(e)
        }

@router.post("/initialize-schema")
async def initialize_schema(admin: Dict = Depends(verify_admin)):
    """Initialize Neo4j schema (constraints and indexes)"""
    if not admin.get("is_super_admin"):
        raise HTTPException(status_code=403, detail="Only super admins can initialize schema")
    
    try:
        from modules.database.services.graph_service import GraphService
        graph_service = GraphService()
        
        # Initialize schema
        result = graph_service.initialize_schema()
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
            
        return result
    except Exception as e:
        logger.error(f"Error initializing schema: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/schools/{school_id}")
async def view_school(request: Request, school_id: str, admin: Dict = Depends(verify_admin)):
    """View school details"""
    try:
        # Fetch school details from Supabase
        result = admin_service.supabase.table("schools").select("*").eq("id", school_id).single().execute()
        school = result.data if result else None
        
        if not school:
            raise HTTPException(status_code=404, detail="School not found")
        
        return templates.TemplateResponse(
            "admin/schools/detail.html",
            {"request": request, "admin": admin, "school": school}
        )
    except Exception as e:
        logger.error(f"Error fetching school details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/schools/{school_id}")
async def delete_school(school_id: str, admin: Dict = Depends(verify_admin)):
    """Delete a school"""
    try:
        # Verify super admin status
        if not admin.get("is_super_admin"):
            raise HTTPException(status_code=403, detail="Only super admins can delete schools")
        
        # Delete the school from Supabase
        result = admin_service.supabase.table("schools").delete().eq("id", school_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="School not found")
        
        return {"status": "success", "message": "School deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting school: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

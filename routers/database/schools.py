from fastapi import APIRouter, Depends, File, UploadFile
from backend.app.run.dependencies import admin_dependency
from pydantic import BaseModel

router = APIRouter()

class NodeBase(BaseModel):
    Name: str

class LocalAuthority(NodeBase):
    pass

class SchoolNode(NodeBase):
    Type: str
    Status: str

class ParliamentaryConstituency(NodeBase):
    pass

class AdministrativeWard(NodeBase):
    pass

class RelationshipBase(BaseModel):
    start_node: NodeBase
    end_node: NodeBase
    relationship_type: str

class HasParliamentaryConstituency(RelationshipBase):
    pass

class HasAdministrativeWard(RelationshipBase):
    pass

class HasSchool(RelationshipBase):
    pass

@router.post("/batch-create-schools")
async def add_school_to_global(file: UploadFile = File(...)):
    if file is None:
        return {"status": "Error", "message": "No file received"}

    try:
        import pandas as pd
        from io import BytesIO
        from app.modules.driver_tools import create_node_http, create_relationship_http
        data = pd.read_csv(BytesIO(await file.read()), usecols=["LA (name)", "ParliamentaryConstituency (name)", "AdministrativeWard (name)", "EstablishmentName", "TypeOfEstablishment (name)", "EstablishmentStatus (name)"])
        unique_las = data["LA (name)"].unique()
        for la_name in unique_las:
            la_node = {"Name": la_name}
            la_id = create_node_http("LocalAuthority", la_node, db="GlobalSchools")
            constituencies = data[data["LA (name)"] == la_name]["ParliamentaryConstituency (name)"].unique()
            for constituency in constituencies:
                constituency_node = {"Name": constituency}
                constituency_id = create_node_http("ParliamentaryConstituency", constituency_node, db="GlobalSchools")
                create_relationship_http({"start_node": {"id": la_id}, "end_node": {"id": constituency_id}, "relationship_type": "HAS_PARLIAMENTARY_CONSTITUENCY"}, db="GlobalSchools")
                wards = data[(data["LA (name)"] == la_name) & (data["ParliamentaryConstituency (name)"] == constituency)]["AdministrativeWard (name)"].unique()
                for ward in wards:
                    ward_node = {"Name": ward}
                    ward_id = create_node_http("AdministrativeWard", ward_node, db="GlobalSchools")
                    create_relationship_http({"start_node": {"id": constituency_id}, "end_node": {"id": ward_id}, "relationship_type": "HAS_ADMINISTRATIVE_WARD"}, db="GlobalSchools")
                    schools = data[(data["LA (name)"] == la_name) & (data["ParliamentaryConstituency (name)"] == constituency) & (data["AdministrativeWard (name)"] == ward)]
                    for index, school in schools.iterrows():
                        school_node = {
                            "Name": school["EstablishmentName"],
                            "Type": school["TypeOfEstablishment (name)"],
                            "Status": school["EstablishmentStatus (name)"]
                        }
                        school_id = create_node_http("School", school_node, db="GlobalSchools")
                        create_relationship_http({"start_node": {"id": ward_id}, "end_node": {"id": school_id}, "relationship_type": "HAS_SCHOOL"}, db="GlobalSchools")
        return {"status": "Success", "message": "Graph structure updated successfully"}
    except Exception as e:
        print("Failed to process file:", e)
        return {"status": "Error", "message": "Failed to process file"}

@router.post("/create-school")
async def add_school_to_global(file: UploadFile = File(...)):
    if file is None:
        return {"status": "Error", "message": "No file received"}

    try:
        import pandas as pd
        from io import BytesIO
        data = pd.read_excel(BytesIO(await file.read()), usecols=[0], nrows=5).squeeze()
        print("Data read from file:", data)
        if len(data) < 5:
            return {"status": "Error", "message": "Insufficient data in file"}
        school_data = {
            "name": data[0],
            "address": data[1],
            "ofsted_number": data[2],
            "website": data[3],
            "geo_location": data[4]
        }
        from app.modules.driver_tools import create_node_http
        response = create_node_http("globalschools", "School", school_data)
        return {"status": "School added to global school db via HTTP", "school_data": school_data, "response": response}
    except Exception as e:
        print("Failed to process file:", e)
        return {"status": "Error", "message": "Failed to process file"}

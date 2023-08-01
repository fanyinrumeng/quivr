from uuid import UUID

from auth import AuthBearer, get_current_user
from fastapi import APIRouter, Depends, Query
from models.brains import Brain
from models.settings import get_supabase_client
from models.users import User
from routes.authorizations.brain_authorization import (
    RoleEnum,
    has_brain_authorization,
    validate_brain_authorization,
)

explore_router = APIRouter()


@explore_router.get("/explore/", dependencies=[Depends(AuthBearer())], tags=["Explore"])
async def explore_endpoint(
    brain_id: UUID = Query(..., description="The ID of the brain"),
):
    """
    Retrieve and explore unique user data vectors.
    """
    brain = Brain(id=brain_id)
    unique_data = brain.get_unique_brain_files()

    unique_data.sort(key=lambda x: int(x["size"]), reverse=True)
    return {"documents": unique_data}


@explore_router.delete(
    "/explore/{file_name}/",
    dependencies=[
        Depends(AuthBearer()),
        Depends(has_brain_authorization(RoleEnum.Owner)),
    ],
    tags=["Explore"],
)
async def delete_endpoint(
    file_name: str,
    current_user: User = Depends(get_current_user),
    brain_id: UUID = Query(..., description="The ID of the brain"),
):
    """
    Delete a specific user file by file name.
    """
    brain = Brain(id=brain_id)
    brain.delete_file_from_brain(file_name)

    return {
        "message": f"{file_name} of brain {brain_id} has been deleted by user {current_user.email}."
    }


@explore_router.get(
    "/explore/{file_name}/", dependencies=[Depends(AuthBearer())], tags=["Explore"]
)
async def download_endpoint(
    file_name: str, current_user: User = Depends(get_current_user)
):
    """
    Download a specific user file by file name.
    """
    # check if user has the right to get the file: add brain_id to the query

    supabase_client = get_supabase_client()
    response = (
        supabase_client.table("vectors")
        .select(
            "metadata->>file_name, metadata->>file_size, metadata->>file_extension, metadata->>file_url",
            "content",
            "brains_vectors(brain_id,vector_id)",
        )
        .match({"metadata->>file_name": file_name})
        .execute()
    )
    documents = response.data

    if len(documents) == 0:
        return {"documents": []}

    related_brain_id = (
        documents[0]["brains_vectors"][0]["brain_id"]
        if len(documents[0]["brains_vectors"]) != 0
        else None
    )

    if related_brain_id is None:
        raise Exception(f"File {file_name} has no brain_id associated with it")

    validate_brain_authorization(brain_id=related_brain_id, user_id=current_user.id)

    return {"documents": documents}

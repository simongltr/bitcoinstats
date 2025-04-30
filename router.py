from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query
from fastapi.openapi.utils import get_openapi
from fastapi.responses import PlainTextResponse

from data import get_blocks_data, get_blocks_data_over_period
from sync import sync
from utils import failure, success

router = APIRouter()


@router.get("/", summary="API documentation")
async def root() -> str:
    """Automatically generated API documentation. Use /docs for a more interactive version. You can also check the OpenAPI schema at /openapi.json."""
    openapi_schema = get_openapi(
        title="Bitcoinstats API v1",
        version="0.1.0",
        routes=router.routes,
    )
    docs = []

    for path, methods in openapi_schema["paths"].items():
        for method, details in methods.items():
            summary = details.get("summary", "No summary")
            docs.append(f"{method.upper()} {path} - {summary}")
            if "description" in details:
                docs.append(f"    {details['description']}")

            if "parameters" in details:
                for param in details["parameters"]:
                    param_name = param.get("name")
                    param_in = param.get("in")
                    param_desc = param.get("description", "No description")
                    param_required = param.get("required", False)
                    docs.append(
                        f"    [{param_in} parameter] '{param_name}' ({'required' if param_required else 'optionnal'}) - {param_desc}"
                    )

            docs.append("")

    return PlainTextResponse("\n".join(docs))


@router.get("/sync", summary="Sync data")
async def sync_data() -> dict:
    """Sync the data to the latest block."""
    try:
        sync()
        return success("Synced")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=failure(str(exc))) from exc


@router.get("/blocks", summary="Get blocks data")
async def get_blocks(
    from_block: Annotated[
        int | None,
        Query(description="The block number to start from"),
    ] = None,
    to_block: Annotated[
        int | None,
        Query(description="The block number to end to"),
    ] = None,
) -> dict:
    """Get the blocks data."""
    try:
        data = get_blocks_data()
        _from = from_block if from_block is not None else 0
        _to = to_block + 1 if to_block is not None else len(data)
        return success(data.iloc[_from:_to].reset_index().to_dict(orient="records"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=failure(str(exc))) from exc


@router.get("/blocks/{period}", summary="Get blocks data over a period")
async def get_blocks_over_period(
    period: Annotated[str, Path(description="The period to group the data by")],
    from_day: Annotated[
        str | None,
        Query(description="The start date to get the data from"),
    ] = None,
    to_day: Annotated[
        str | None,
        Query(description="The end date to get the data to"),
    ] = None,
) -> dict:
    """Get the blocks data over a period."""
    if period not in ["daily", "monthly"]:
        raise HTTPException(
            status_code=400,
            detail=failure("The period must be 'daily' or 'monthly'"),
        )

    try:
        data = get_blocks_data_over_period(
            period=period,
            from_day=from_day,
            to_day=to_day,
        )
        return success(data.reset_index().to_dict(orient="records"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=failure(str(exc))) from exc

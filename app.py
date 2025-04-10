import asyncio
from datetime import datetime
from typing import List

from fastapi import FastAPI, Depends, Query
from fastapi.responses import Response
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from asyncdb.db import SessionLocal
from asyncdb.models import ProductModel
from asyncdb.pydantic_models import Product, ProductPayload, \
    ProductWithExtraData, PaginatedProductResponse, ProductUpdate
from asyncdb import queries
from django_api.api import get_django_product_info

app = FastAPI()


async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


@app.get("/products",

         response_model=PaginatedProductResponse)
async def read_products(
        offset=Query(0),
        limit=Query(10),
        db: AsyncSession = Depends(get_db)
):
    products_models = await queries.get_products(db, offset, limit)

    count_query = select([func.count()]).select_from(ProductModel)
    total = (await db.execute(count_query)).scalar()

    products = [Product.from_orm(product) for product in products_models]

    return PaginatedProductResponse(
        results=products,
        total=total,
        offset=offset,
        limit=limit
    )

    # start = datetime.now()
    # django_products = await asyncio.gather(
    #     *[get_django_product_info(product.name) for product in products]
    # )
    # end = datetime.now()
    #
    # print(f"Time taken: {(end - start)}")
    #
    # products_with_extra_data = []
    # for product, django_product in zip(products, django_products):
    #     products_with_extra_data.append(
    #         ProductWithExtraData(
    #             **product.dict(),
    #             extra_data=django_product
    #         )
    #     )
    #
    # return products_with_extra_data


@app.post("/products", response_model=Product)
async def create_product(product_payload: ProductPayload, db: AsyncSession = Depends(get_db)):
    async with db as session:
        db_product = ProductModel(**product_payload.dict())
        session.add(db_product)
        await session.commit()
        await session.refresh(db_product)
        return db_product


@app.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    product_model = await queries.search_product(db, product_id)

    if not product_model:
        return Response(status_code=404)

    return Product.from_orm(product_model)


@app.put("/products/{product_id}", response_model=Product)
async def update_product(
        product_id: int,
        product_payload: ProductPayload,
        db: AsyncSession = Depends(get_db)
        ):
    updated = await queries.update_product(db, product_id, product_payload)

    if not updated:
        return Response(status_code=404)

    return Product.from_orm(
        await queries.search_product(db, product_id)
    )


@app.patch("/products/{product_id}", response_model=Product)
async def patch_product(
        product_id: int,
        product_update: ProductUpdate,
        db: AsyncSession = Depends(get_db)
        ):
    updated = await queries.partial_update_product(db, product_id, product_update)

    if not updated:
        return Response(status_code=404)

    return Product.from_orm(
        await queries.search_product(db, product_id)
    )


@app.delete("/products/{product_id}")
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db)):
    updated = await queries.delete_product(db, product_id)

    if not updated:
        return Response(status_code=404)

    return Response(status_code=204)

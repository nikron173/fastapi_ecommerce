from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_seller
from app.models import (
    Category as CategoryModel,
    Product as ProductModel,
    User as UserModel,
    Review as ReviewModel
)
from app.schemas import Product as ProductSchema, ProductCreate, Review as ReviewSchema
from app.db_depends import get_async_db


# Создаём маршрутизатор для товаров
router = APIRouter(
    prefix="/products",
    tags=["products"],
)


@router.get("/", response_model=list[ProductSchema])
async def get_all_products(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех товаров.
    """
    result = await db.scalars(
        select(ProductModel).join(CategoryModel).where(
            ProductModel.is_active == True,
            CategoryModel.is_active == True,
            ProductModel.stock > 0,
        )
    )
    products = result.all()
    return products


@router.post("/", response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
async def create_product(
        product: ProductCreate,
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_seller)
):
    """
    Создаёт новый товар, привязанный к текущему продавцу (только для 'seller').
    """
    rs_category = await db.scalars(
        select(CategoryModel).where(
            CategoryModel.id == product.category_id,
            CategoryModel.is_active == True
        )
    )
    category = rs_category.first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not found or inactive",
        )

    db_product = ProductModel(**product.model_dump(), seller_id=current_user.id)
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)

    return db_product


@router.get("/category/{category_id}", response_model=list[ProductSchema])
async def get_products_by_category(
        category_id: int,
        db: AsyncSession = Depends(get_async_db)
):
    """
    Возвращает список товаров в указанной категории по её ID.
    """
    rs_category = await db.scalars(
        select(CategoryModel).where(
        CategoryModel.id == category_id,
        CategoryModel.is_active == True,
        )
    )
    category = rs_category.first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not found or inactive",
        )

    rs_products = await db.scalars(
        select(ProductModel).where(
            ProductModel.category_id == category_id,
            ProductModel.is_active == True
        )
    )
    products = rs_products.all()

    return products


@router.get("/{product_id}", response_model=ProductSchema)
async def get_product(
        product_id: int,
        db: AsyncSession = Depends(get_async_db)
):
    """
    Возвращает детальную информацию о товаре по его ID.
    """
    rs_product = await db.scalars(
        select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)
    )
    product = rs_product.first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    rs_category = await db.scalars(
        select(CategoryModel).where(
            CategoryModel.id == product.category_id,
            CategoryModel.is_active == True,
        )
    )
    category = rs_category.first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not found or inactive",
        )

    return product


@router.put("/{product_id}", response_model=ProductSchema)
async def update_product(
        product_id: int,
        product: ProductCreate,
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_seller)
):
    """
    Обновляет товар, если он принадлежит текущему продавцу (только для 'seller').
    """
    rs_db_product = await db.scalars(
        select(ProductModel).where(
            ProductModel.id == product_id,
            ProductModel.is_active == True,
        )
    )
    db_product = rs_db_product.first()
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    if db_product.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own products"
        )

    rs_category = await db.scalars(
        select(CategoryModel).where(
            CategoryModel.id == product.category_id,
            CategoryModel.is_active == True
        )
    )
    category = rs_category.first()
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not found or inactive",
        )

    await db.execute(
        update(ProductModel)
        .where(ProductModel.id == product_id)
        .values(**product.model_dump())
    )
    await db.commit()
    await db.refresh(db_product)

    return db_product


@router.delete("/{product_id}")
async def delete_product(
        product_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_seller)
):
    """
    Удаляет товар по его ID.
    """
    rs_product = await db.scalars(
        select(ProductModel).where(
            ProductModel.id == product_id,
            ProductModel.is_active == True,
            ProductModel.price.between()
        )
    )
    product = rs_product.first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    if product.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own products"
        )

    rs_category = await db.scalars(
        select(CategoryModel).where(
            CategoryModel.id == product.category_id,
            CategoryModel.is_active == True,

        )
    )
    category = rs_category.first()
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not found or inactive",
        )

    await db.execute(
        update(ProductModel)
        .where(ProductModel.id == product_id)
        .values(is_active=False)
    )
    await db.commit()
    await db.refresh(product)

    return product


@router.get("/{product_id}/reviews/", response_model=list[ReviewSchema])
async def get_reviews(
        product_id: int,
        db: AsyncSession = Depends(get_async_db)
):
    rs_product = await db.scalars(
        select(ProductModel).where(
            ProductModel.id == product_id,
            ProductModel.is_active == True,
        )
    )
    product = rs_product.first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    rs_reviews = await db.scalars(
        select(ReviewModel).where(
            ReviewModel.is_active == True,
            ReviewModel.product_id == product.id,
        )
    )
    reviews = rs_reviews.all()
    return reviews

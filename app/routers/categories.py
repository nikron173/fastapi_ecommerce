from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.categories import Category as CategoryModel
from app.schemas import Category as CategorySchema, CategoryCreate
from app.db_depends import get_async_db


# Создаём маршрутизатор с префиксом и тегом
router = APIRouter(
    prefix="/categories",
    tags=["categories"],
)


@router.get("/", response_model=list[CategorySchema])
async def get_all_categories(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех категорий товаров.
    """
    result = await db.scalars(
        select(CategoryModel).where(CategoryModel.is_active == True)
    )
    categories = result.all()
    return categories


@router.post("/", response_model=CategorySchema, status_code=status.HTTP_201_CREATED)
async def create_category(
        category: CategoryCreate,
        db: AsyncSession = Depends(get_async_db)
):
    """
    Создаёт новую категорию.
    """
    # Проверка существования parent_id, если указан
    if category.parent_id is not None:
        result = await db.scalars(select(CategoryModel).where(CategoryModel.id == category.parent_id))
        parent = result.first()
        if parent is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Parent category not found")

    # Создание новой категории
    db_category = CategoryModel(**category.model_dump())
    db.add(db_category)
    await db.commit()
    await db.refresh(db_category)
    return db_category


@router.put("/{category_id}", response_model=CategorySchema)
async def update_category(
        category_id: int,
        category: CategoryCreate,
        db: AsyncSession = Depends(get_async_db)
):
    """
    Обновляет категорию по её ID.
    """
    result = await db.scalars(
        select(CategoryModel).where(CategoryModel.id == category_id)
    )
    db_category = result.first()
    if not db_category:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Category not found")

    if category.parent_id is not None:
        parent_result = await db.scalars(
            select(CategoryModel).where(CategoryModel.id == category.parent_id)
        )
        parent = parent_result.first()
        if parent is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Parent category not found")
        if parent.id == category_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Category cannot be its own parent")

    update_data = category.model_dump(exclude_unset=True)
    await db.execute(
        update(CategoryModel)
        .where(CategoryModel.id == category_id)
        .values(**update_data)
    )
    await db.commit()
    await db.refresh(db_category)

    return db_category


@router.delete("/{category_id}", status_code=status.HTTP_200_OK)
async def delete_category(category_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Удаляет категорию по её ID.
    """
    result = await db.scalar(
        select(CategoryModel.id).where(
            CategoryModel.id == category_id,
            CategoryModel.is_active == True,
        )
    )
    category = result.first()
    if category is None:
        raise HTTPException(status_code=400, detail="Category not found")

    await db.execute(
        update(CategoryModel).where(CategoryModel.id == category_id).values(is_active=False)
    )
    await db.commit()
    return {"status": "success", "message": "Category marked as inactive"}

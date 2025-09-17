from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_depends import get_async_db
from app.auth import get_current_user, get_current_admin
from app.models import (
    Review as ReviewModel,
    User as UserModel,
    Product as ProductModel,
)
from app.schemas import Review as ReviewSchema, ReviewCreate


router = APIRouter(
    prefix="/reviews",
    tags=["reviews"]
)


@router.get("/", response_model=list[ReviewSchema])
async def get_reviews(db: AsyncSession = Depends(get_async_db)):
    """
    Получение всех комментариев по всем товарам
    """
    rs_reviews = await db.scalars(
        select(ReviewModel).where(ReviewModel.is_active == True)
    )
    reviews = rs_reviews.all()
    return reviews


@router.post("/", response_model=ReviewSchema, status_code=status.HTTP_201_CREATED)
async def create_review(
        review: ReviewCreate,
        current_user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_db)
):
    """
    Создание нового комментария по товару, доступно только пользователям с ролью buyer
    """
    if current_user.role != "buyer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только аутентифицированные пользователи с ролью \"buyer\""
        )
    if review.grade < 1 or review.grade > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="grade вне диапазона [1–5]."
        )

    rs_product = await db.scalars(
        select(ProductModel).where(
            ProductModel.is_active == True,
            ProductModel.id == review.product_id,
        )
    )
    product = rs_product.first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or inactive"
        )

    db_review = ReviewModel(**review.model_dump(), user_id=current_user.id)
    db.add(db_review)

    await db.commit()
    await db.refresh(db_review)
    await update_product_rating(db, product.id)

    return db_review


@router.delete("/{review_id}", status_code=status.HTTP_200_OK)
async def delete_review(
        review_id: int,
        current_user: UserModel = Depends(get_current_admin),
        db: AsyncSession = Depends(get_async_db)
):
    """
    Логическое удаление комментария, доступно только пользователям с ролью admin
    """
    rs_review = await db.scalars(
        select(ReviewModel).where(
            ReviewModel.id == review_id,
            ReviewModel.is_active == True,
        )
    )
    review = rs_review.first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found or inactive"
        )

    rs_product = await db.scalars(
        select(ProductModel).where(
            ProductModel.id == review.product_id,
            ProductModel.is_active == True,
        )
    )
    product = rs_product.first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or inactive"
        )

    await db.execute(
        update(ReviewModel).where(ReviewModel.id == review.id).values(is_active=False)
    )
    await db.commit()
    await update_product_rating(db, product.id)

    return {"message": "Review deleted"}


async def update_product_rating(db: AsyncSession, product_id: int):
    result = await db.execute(
        select(func.avg(ReviewModel.grade)).where(
            ReviewModel.product_id == product_id,
            ReviewModel.is_active == True
        )
    )
    avg_rating = result.scalar() or 0.0
    product = await db.get(ProductModel, product_id)
    product.rating = avg_rating
    await db.commit()

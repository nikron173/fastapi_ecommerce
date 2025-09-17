from sqlalchemy import ForeignKey, Text, CheckConstraint, Integer, DateTime, Boolean
from sqlalchemy.orm import relationship, mapped_column, Mapped
from datetime import datetime

from app.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    comment_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    grade: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint("grade >= 1 AND grade <= 5", name="check_grade_comment"),
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    buyer: Mapped["User"] = relationship("User", back_populates="reviews")
    product: Mapped["Product"] = relationship("Product", back_populates="reviews")

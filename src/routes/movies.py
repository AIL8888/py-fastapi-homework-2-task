from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database import MovieModel, get_db
from database.models import ActorModel, CountryModel, GenreModel, LanguageModel
from schemas.movies import (
    MessageSchema,
    MovieCreateSchema,
    MovieDetailSchema,
    MovieListItemSchema,
    MovieListResponseSchema,
    MovieUpdateSchema,
)


router = APIRouter()


async def _get_or_create_country(db: AsyncSession, code: str) -> CountryModel:
    stmt = select(CountryModel).where(CountryModel.code == code)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        return existing

    country = CountryModel(code=code, name=None)
    db.add(country)
    await db.flush()
    return country


async def _get_or_create_by_name(db: AsyncSession, model: type, name: str):
    stmt = select(model).where(model.name == name)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        return existing

    obj = model(name=name)
    db.add(obj)
    await db.flush()
    return obj


def _page_link(page: int, per_page: int) -> str:
    return f"/theater/movies/?page={page}&per_page={per_page}"


@router.get("/movies/", response_model=MovieListResponseSchema)
async def list_movies(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    total_items = await db.scalar(select(func.count(MovieModel.id)))

    if not total_items:
        raise HTTPException(status_code=404, detail="No movies found.")

    total_pages = (total_items + per_page - 1) // per_page

    if page > total_pages:
        raise HTTPException(status_code=404, detail="No movies found.")

    offset = (page - 1) * per_page

    stmt = (
        select(MovieModel)
        .order_by(MovieModel.id.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    movies = result.scalars().all()

    if not movies:
        raise HTTPException(status_code=404, detail="No movies found.")

    prev_page = _page_link(page - 1, per_page) if page > 1 else None
    next_page = _page_link(page + 1, per_page) if page < total_pages else None

    return MovieListResponseSchema(
        movies=[MovieListItemSchema.model_validate(m) for m in movies],
        prev_page=prev_page,
        next_page=next_page,
        total_pages=total_pages,
        total_items=total_items,
    )


@router.get("/movies/{movie_id}/", response_model=MovieDetailSchema)
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(MovieModel)
        .where(MovieModel.id == movie_id)
        .options(
            joinedload(MovieModel.country),
            joinedload(MovieModel.genres),
            joinedload(MovieModel.actors),
            joinedload(MovieModel.languages),
        )
    )
    result = await db.execute(stmt)
    movie = result.scalars().unique().one_or_none()

    if movie is None:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    return MovieDetailSchema.model_validate(movie)


@router.post("/movies/", response_model=MovieDetailSchema, status_code=status.HTTP_201_CREATED)
async def create_movie(payload: MovieCreateSchema, db: AsyncSession = Depends(get_db)):
    exists_stmt = select(MovieModel.id).where(
        MovieModel.name == payload.name,
        MovieModel.date == payload.date,
    )
    exists = (await db.execute(exists_stmt)).scalar_one_or_none()
    if exists is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"A movie with the name '{payload.name}' and release date '{payload.date.isoformat()}' already exists."
            ),
        )

    country = await _get_or_create_country(db, payload.country)
    genres = [await _get_or_create_by_name(db, GenreModel, name) for name in payload.genres]
    actors = [await _get_or_create_by_name(db, ActorModel, name) for name in payload.actors]
    languages = [await _get_or_create_by_name(db, LanguageModel, name) for name in payload.languages]

    movie = MovieModel(
        name=payload.name,
        date=payload.date,
        score=payload.score,
        overview=payload.overview,
        status=payload.status,
        budget=payload.budget,
        revenue=payload.revenue,
        country=country,
        genres=genres,
        actors=actors,
        languages=languages,
    )

    db.add(movie)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=(
                f"A movie with the name '{payload.name}' and release date '{payload.date.isoformat()}' already exists."
            ),
        )

    stmt = (
        select(MovieModel)
        .where(MovieModel.id == movie.id)
        .options(
            joinedload(MovieModel.country),
            joinedload(MovieModel.genres),
            joinedload(MovieModel.actors),
            joinedload(MovieModel.languages),
        )
    )
    result = await db.execute(stmt)
    movie = result.scalars().unique().one()

    return MovieDetailSchema.model_validate(movie)


@router.delete("/movies/{movie_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(MovieModel).where(MovieModel.id == movie_id)
    movie = (await db.execute(stmt)).scalar_one_or_none()

    if movie is None:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    await db.delete(movie)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/movies/{movie_id}/", response_model=MessageSchema)
async def update_movie(movie_id: int, payload: MovieUpdateSchema, db: AsyncSession = Depends(get_db)):
    stmt = select(MovieModel).where(MovieModel.id == movie_id)
    movie = (await db.execute(stmt)).scalar_one_or_none()

    if movie is None:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(movie, field, value)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Invalid input data.")

    return MessageSchema(detail="Movie updated successfully.")

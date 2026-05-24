from __future__ import annotations

from app.db.models import Block, Lecture, Section
from app.db.repositories.catalog import CatalogRepository
from app.services.catalog.dto import BlockDTO, LectureDTO, SectionDTO


class CatalogService:
    def __init__(self, repository: CatalogRepository) -> None:
        self._repository = repository

    async def list_sections(self) -> list[SectionDTO]:
        return [self._section_to_dto(section) for section in await self._repository.list_sections()]

    async def get_section(self, section_id: int) -> SectionDTO | None:
        section = await self._repository.get_section(section_id)
        if section is None:
            return None
        return self._section_to_dto(section)

    async def list_blocks(self, section_id: int) -> list[BlockDTO]:
        return [self._block_to_dto(block) for block in await self._repository.list_blocks(section_id)]

    async def get_block(self, block_id: int) -> BlockDTO | None:
        block = await self._repository.get_block(block_id)
        if block is None:
            return None
        return self._block_to_dto(block)

    async def list_lectures(self, block_id: int) -> list[LectureDTO]:
        return [
            self._lecture_to_dto(lecture)
            for lecture in await self._repository.list_lectures(block_id)
        ]

    async def get_lecture(self, lecture_id: int) -> LectureDTO | None:
        lecture = await self._repository.get_lecture(lecture_id)
        if lecture is None:
            return None
        return self._lecture_to_dto(lecture)

    @staticmethod
    def _section_to_dto(section: Section) -> SectionDTO:
        return SectionDTO(
            id=section.id,
            title=section.title,
            description=section.description,
        )

    @staticmethod
    def _block_to_dto(block: Block) -> BlockDTO:
        return BlockDTO(
            id=block.id,
            section_id=block.section_id,
            title=block.title,
            description=block.description,
            price=block.price,
        )

    @staticmethod
    def _lecture_to_dto(lecture: Lecture) -> LectureDTO:
        return LectureDTO(
            id=lecture.id,
            block_id=lecture.block_id,
            title=lecture.title,
            short_description=lecture.short_description,
            full_description=lecture.full_description,
            price=lecture.price,
        )

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.logging import configure_logging
from app.db.models import Block, Lecture, Section
from app.db.session import async_session_factory


@dataclass(frozen=True)
class LectureSeed:
    title: str
    short_description: str
    full_description: str
    price: Decimal
    sort_order: int


@dataclass(frozen=True)
class BlockSeed:
    title: str
    description: str
    price: Decimal
    sort_order: int
    lectures: tuple[LectureSeed, ...]


@dataclass(frozen=True)
class SectionSeed:
    title: str
    description: str
    sort_order: int
    blocks: tuple[BlockSeed, ...]


DEMO_CATALOG: tuple[SectionSeed, ...] = (
    SectionSeed(
        title="Фармакология",
        description="Базовые и клинические темы по лекарственным средствам.",
        sort_order=10,
        blocks=(
            BlockSeed(
                title="Антибиотики",
                description="Классы антибиотиков, спектры активности, безопасность и клинический выбор.",
                price=Decimal("2990.00"),
                sort_order=10,
                lectures=(
                    LectureSeed(
                        title="Пенициллины",
                        short_description="Классификация, показания, устойчивость и аллергические реакции.",
                        full_description=(
                            "Разбор природных, антистафилококковых, аминопенициллинов и "
                            "ингибиторозащищённых препаратов."
                        ),
                        price=Decimal("790.00"),
                        sort_order=10,
                    ),
                    LectureSeed(
                        title="Цефалоспорины",
                        short_description="Поколения цефалоспоринов и клинические сценарии применения.",
                        full_description="Сравнение поколений, спектров активности и типичных ошибок назначения.",
                        price=Decimal("790.00"),
                        sort_order=20,
                    ),
                    LectureSeed(
                        title="Макролиды и линкозамиды",
                        short_description="Препараты для респираторных инфекций и атипичной флоры.",
                        full_description="Фокус на азитромицине, кларитромицине, клиндамицине и безопасности.",
                        price=Decimal("690.00"),
                        sort_order=30,
                    ),
                    LectureSeed(
                        title="Фторхинолоны",
                        short_description="Показания, ограничения и риски нежелательных реакций.",
                        full_description="Когда фторхинолоны оправданы и почему их не стоит назначать рутинно.",
                        price=Decimal("690.00"),
                        sort_order=40,
                    ),
                ),
            ),
            BlockSeed(
                title="НПВС и анальгетики",
                description="Обезболивание, противовоспалительная терапия и управление рисками.",
                price=Decimal("1990.00"),
                sort_order=20,
                lectures=(
                    LectureSeed(
                        title="Ибупрофен и напроксен",
                        short_description="Выбор препарата, дозировки и безопасность.",
                        full_description="Практические схемы применения и ограничения по группам пациентов.",
                        price=Decimal("590.00"),
                        sort_order=10,
                    ),
                    LectureSeed(
                        title="Диклофенак и кеторолак",
                        short_description="Сильное обезболивание и оценка рисков.",
                        full_description="Кардиоваскулярные, ЖКТ и почечные риски при назначении НПВС.",
                        price=Decimal("590.00"),
                        sort_order=20,
                    ),
                    LectureSeed(
                        title="Парацетамол",
                        short_description="Жаропонижающая терапия и токсичность.",
                        full_description="Дозирование, передозировка, поражение печени и комбинации препаратов.",
                        price=Decimal("490.00"),
                        sort_order=30,
                    ),
                ),
            ),
            BlockSeed(
                title="Сердечно-сосудистые препараты",
                description="Основные группы препаратов для терапии сердечно-сосудистых заболеваний.",
                price=Decimal("3490.00"),
                sort_order=30,
                lectures=(
                    LectureSeed(
                        title="Антигипертензивные препараты",
                        short_description="Ингибиторы АПФ, БРА, БКК, диуретики и бета-блокаторы.",
                        full_description="Алгоритмы выбора терапии гипертонии и частые лекарственные комбинации.",
                        price=Decimal("890.00"),
                        sort_order=10,
                    ),
                    LectureSeed(
                        title="Антикоагулянты и антиагреганты",
                        short_description="Профилактика тромбозов и безопасность терапии.",
                        full_description="Варфарин, ПОАК, аспирин, клопидогрел и контроль кровотечений.",
                        price=Decimal("890.00"),
                        sort_order=20,
                    ),
                    LectureSeed(
                        title="Статины и гиполипидемические средства",
                        short_description="Коррекция липидов и профилактика сердечно-сосудистого риска.",
                        full_description="Выбор интенсивности терапии, мониторинг и нежелательные реакции.",
                        price=Decimal("790.00"),
                        sort_order=30,
                    ),
                ),
            ),
        ),
    ),
    SectionSeed(
        title="Клиническая фармакология",
        description="Прикладные темы: безопасность, взаимодействия и особые группы пациентов.",
        sort_order=20,
        blocks=(
            BlockSeed(
                title="Лекарственные взаимодействия",
                description="Как прогнозировать и предотвращать клинически значимые взаимодействия.",
                price=Decimal("2490.00"),
                sort_order=10,
                lectures=(
                    LectureSeed(
                        title="CYP450 и P-gp",
                        short_description="Ферменты, транспортеры и практическая оценка взаимодействий.",
                        full_description="Ингибиторы, индукторы, субстраты и клинические последствия.",
                        price=Decimal("790.00"),
                        sort_order=10,
                    ),
                    LectureSeed(
                        title="Опасные комбинации препаратов",
                        short_description="Комбинации, которые требуют отмены, замены или мониторинга.",
                        full_description="Серотониновый синдром, удлинение QT, кровотечения и нефротоксичность.",
                        price=Decimal("790.00"),
                        sort_order=20,
                    ),
                    LectureSeed(
                        title="Полипрагмазия",
                        short_description="Рациональная депрескрайбинг-стратегия.",
                        full_description="Как пересматривать назначения и снижать лекарственную нагрузку.",
                        price=Decimal("690.00"),
                        sort_order=30,
                    ),
                ),
            ),
            BlockSeed(
                title="Особые группы пациентов",
                description="Беременность, дети, пожилые пациенты, почечная и печеночная недостаточность.",
                price=Decimal("2490.00"),
                sort_order=20,
                lectures=(
                    LectureSeed(
                        title="Беременность и лактация",
                        short_description="Оценка риска и выбор безопасной терапии.",
                        full_description="Принципы назначения и источники проверки безопасности препаратов.",
                        price=Decimal("790.00"),
                        sort_order=10,
                    ),
                    LectureSeed(
                        title="Педиатрическая фармакология",
                        short_description="Дозирование и безопасность препаратов у детей.",
                        full_description="Возрастные ограничения, формы выпуска и типичные ошибки дозирования.",
                        price=Decimal("790.00"),
                        sort_order=20,
                    ),
                    LectureSeed(
                        title="Пожилые пациенты",
                        short_description="Фармакокинетика, падения, когнитивные риски и депрескрайбинг.",
                        full_description="STOPP/START-подход, антихолинергическая нагрузка и мониторинг терапии.",
                        price=Decimal("690.00"),
                        sort_order=30,
                    ),
                ),
            ),
        ),
    ),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed demo pharmacology catalog.")
    parser.add_argument(
        "--inactive",
        action="store_true",
        help="Create or update seeded sections, blocks and lectures as inactive.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be created or updated without writing to database.",
    )
    return parser


async def seed_demo_catalog(*, is_active: bool, dry_run: bool) -> tuple[int, int, int]:
    async with async_session_factory() as session:
        stats = (0, 0, 0)
        for section_seed in DEMO_CATALOG:
            section, section_created = await _get_or_create_section(
                session,
                section_seed,
                is_active=is_active,
                dry_run=dry_run,
            )
            stats = _add_stats(stats, section_created, 0, 0)

            for block_seed in section_seed.blocks:
                block, block_created = await _get_or_create_block(
                    session,
                    section,
                    block_seed,
                    is_active=is_active,
                    dry_run=dry_run,
                )
                stats = _add_stats(stats, 0, block_created, 0)

                for lecture_seed in block_seed.lectures:
                    _, lecture_created = await _get_or_create_lecture(
                        session,
                        block,
                        lecture_seed,
                        is_active=is_active,
                        dry_run=dry_run,
                    )
                    stats = _add_stats(stats, 0, 0, lecture_created)

        if dry_run:
            await session.rollback()
        else:
            await session.commit()
        return stats


async def _get_or_create_section(
    session: AsyncSession,
    seed: SectionSeed,
    *,
    is_active: bool,
    dry_run: bool,
) -> tuple[Section, int]:
    existing = await session.scalar(select(Section).where(Section.title == seed.title))
    if existing is not None:
        existing.description = seed.description
        existing.sort_order = seed.sort_order
        existing.is_active = is_active
        return existing, 0

    section = Section(
        title=seed.title,
        description=seed.description,
        sort_order=seed.sort_order,
        is_active=is_active,
    )
    session.add(section)
    if not dry_run:
        await session.flush()
    else:
        await session.flush()
    return section, 1


async def _get_or_create_block(
    session: AsyncSession,
    section: Section,
    seed: BlockSeed,
    *,
    is_active: bool,
    dry_run: bool,
) -> tuple[Block, int]:
    existing = await session.scalar(
        select(Block).where(
            Block.section_id == section.id,
            Block.title == seed.title,
        ),
    )
    if existing is not None:
        existing.description = seed.description
        existing.price = seed.price
        existing.sort_order = seed.sort_order
        existing.is_active = is_active
        return existing, 0

    block = Block(
        section_id=section.id,
        title=seed.title,
        description=seed.description,
        price=seed.price,
        sort_order=seed.sort_order,
        is_active=is_active,
    )
    session.add(block)
    if not dry_run:
        await session.flush()
    else:
        await session.flush()
    return block, 1


async def _get_or_create_lecture(
    session: AsyncSession,
    block: Block,
    seed: LectureSeed,
    *,
    is_active: bool,
    dry_run: bool,
) -> tuple[Lecture, int]:
    existing = await session.scalar(
        select(Lecture).where(
            Lecture.block_id == block.id,
            Lecture.title == seed.title,
        ),
    )
    if existing is not None:
        existing.short_description = seed.short_description
        existing.full_description = seed.full_description
        existing.price = seed.price
        existing.sort_order = seed.sort_order
        existing.is_active = is_active
        return existing, 0

    lecture = Lecture(
        block_id=block.id,
        title=seed.title,
        short_description=seed.short_description,
        full_description=seed.full_description,
        price=seed.price,
        sort_order=seed.sort_order,
        is_active=is_active,
    )
    session.add(lecture)
    await session.flush()
    return lecture, 1


def _add_stats(
    stats: tuple[int, int, int],
    sections: int,
    blocks: int,
    lectures: int,
) -> tuple[int, int, int]:
    return (
        stats[0] + sections,
        stats[1] + blocks,
        stats[2] + lectures,
    )


def main() -> None:
    configure_logging()
    args = build_parser().parse_args()
    section_count, block_count, lecture_count = asyncio.run(
        seed_demo_catalog(
            is_active=not args.inactive,
            dry_run=args.dry_run,
        ),
    )
    action = "would be created" if args.dry_run else "created"
    print(
        "Demo catalog seed completed: "
        f"sections {action}: {section_count}, "
        f"blocks {action}: {block_count}, "
        f"lectures {action}: {lecture_count}."
    )


if __name__ == "__main__":
    main()

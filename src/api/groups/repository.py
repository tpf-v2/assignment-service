from sqlalchemy import func, bindparam, update, select, insert, asc
from sqlalchemy.orm import Session, joinedload

from src.api.groups.exceptions import GroupNotFound
from src.api.groups.models import Group, association_table
from src.api.students.exceptions import StudentNotFound
from src.api.users.models import User


class GroupRepository:

    def __init__(self, sess: Session):
        self.Session = sess

    def add_group(
        self,
        ids,
        tutor_period_id=None,
        topic_id=None,
        preferred_topics=[],
        period_id=None,
    ):
        """Inserta un grupo a partir de los diferentes parametros"""
        with self.Session() as session:
            students = session.query(User).filter(User.id.in_(ids)).all()
            if len(students) != len(ids):
                raise StudentNotFound(message="Some ids are not in database")

            group = Group(
                tutor_period_id=tutor_period_id,
                assigned_topic_id=topic_id,
                preferred_topics=preferred_topics,
                period_id=period_id,
            )
            group.students = students
            session.add(group)
            session.commit()
            session.refresh(group)

            group.group_number = group.id
            session.commit()
            session.refresh(group)
            session.expunge(group)

        return group

    def add_group_having_emails(
        self,
        emails,
        tutor_period_id=None,
        topic_id=None,
        preferred_topics=[],
        period_id=None,
    ):
        """Inserta un grupo a partir de los emails de los estudiantes"""
        with self.Session() as session:
            students = session.query(User).filter(User.email.in_(emails)).all()
            if len(students) != len(emails):
                raise StudentNotFound(message="Some ids are not in database")
            group = Group(
                tutor_period_id=tutor_period_id,
                assigned_topic_id=topic_id,
                preferred_topics=preferred_topics,
                period_id=period_id,
            )
            group.students = students
            session.add(group)
            session.commit()
            session.refresh(group)

            group.group_number = group.id
            session.commit()
            session.expunge(group)

        return group

    def get_groups(
        self,
        period: str,
        load_topic=False,
        load_tutor_period=False,
        load_period=False,
        load_students=False,
        load_dates: bool = False,
    ) -> list[Group]:
        """Devuelve los grupos a partir de un cuatrimestre y diferentes filtros"""
        with self.Session() as session:
            query = session.query(Group)

            if load_topic:
                query = query.options(joinedload(Group.topic))
            if load_tutor_period:
                query = query.options(joinedload(Group.tutor_period))
            if load_period:
                query = query.options(joinedload(Group.period))
            if load_students:
                query = query.options(joinedload(Group.students))
            if load_dates:
                query = query.options(joinedload(Group.group_dates_slots))

            groups = (
                query.filter(Group.period_id == period).order_by(asc(Group.id)).all()
            )
            session.expunge_all()
        return groups

    def get_groups_without_tutor_and_period(self) -> list[Group]:
        """Devuelve los grupos que no tiene ni tutor ni tema asignado"""
        with self.Session() as session:
            groups = (
                session.query(Group)
                .filter(Group.assigned_topic_id.is_(None))
                .filter(Group.tutor_period_id.is_(None))
                .all()
            )
            session.expunge_all()

        return groups

    def get_groups_without_preferred_topics(self, period) -> list[Group]:
        """Devuelve todos los grupos que no tengan temas de preferencias"""
        with self.Session() as session:
            groups = (
                session.query(Group)
                .filter(
                    func.cardinality(Group.preferred_topics) == 0,
                    Group.period_id == period,
                )
                .all()
            )
            session.expunge_all()

        return groups

    def get_groups_learning_path(self, period) -> list[Group]:
        """Devuelve todos los grupos de un cuatrimestre"""
        with self.Session() as session:
            groups = session.query(Group).filter(Group.period_id == period).all()
        return groups

    def update(self, group_id, attributes: dict):
        """Actualiza el group_id a partir de los atributos que sean provistos"""
        stmt = update(Group).where(Group.id == group_id).values(**attributes)
        with self.Session() as session:
            session.execute(stmt)
            session.commit()

    def get_groups_by_period_id(
        self,
        tutor_period_id: int,
        load_topic=False,
        load_period=False,
        load_students=False,
    ) -> list[Group]:
        """Devuelve todos los grupo basado en un TutorPeriod id"""
        with self.Session() as session:
            query = session.query(Group).options(joinedload(Group.tutor_period))

            if load_topic:
                query = query.options(joinedload(Group.topic))
            if load_period:
                query = query.options(joinedload(Group.period))
            if load_students:
                query = query.options(joinedload(Group.students))

            groups = query.filter(Group.tutor_period_id == tutor_period_id).all()
            session.expunge_all()
            session.expunge_all()
        return groups

    def get_group_by_id(
        self,
        group_id,
        load_topic=False,
        load_period=False,
        load_students=False,
        load_tutor=False,
    ) -> Group:
        """Devuelve el grupo basado en un id"""

        with self.Session() as session:
            query = session.query(Group)
            if load_topic:
                query = query.options(joinedload(Group.topic))
            if load_period:
                query = query.options(joinedload(Group.period))
            if load_students:
                query = query.options(joinedload(Group.students))
            if load_tutor:
                query = query.options(joinedload(Group.tutor_period))

            group = query.filter(Group.id == group_id).one_or_none()
            if group is None:
                raise GroupNotFound(message=f"{group_id} not found in db")

            session.expunge(group)
        return group

    def get_group_by_student_id(self, student_id: int) -> Group:
        with self.Session() as session:
            result = (
                session.query(association_table.c.group_id.label("id"))
                .filter_by(student_id=student_id)
                .one_or_none()
            )
            if result is None:
                raise GroupNotFound(message=f"{result.id} not found in db")

            group = session.query(Group).filter(Group.id == result.id).one_or_none()
            session.expunge(group)
        return group

    def get_groups_by_reviewer_id(
        self,
        reviewer_id: int,
        period_id: str,
        load_topic=False,
        load_period=False,
        load_students=False,
        load_tutor_period=False,
    ) -> list[Group]:
        """Devuelve todos los grupos para un reviewer_id y period_id dados"""

        with self.Session() as session:
            query = session.query(Group)

            if load_topic:
                query = query.options(joinedload(Group.topic))
            if load_tutor_period:
                query = query.options(joinedload(Group.tutor_period))
            if load_period:
                query = query.options(joinedload(Group.period))
            if load_students:
                query = query.options(joinedload(Group.students))

            groups = query.filter(
                Group.period_id == period_id, Group.reviewer_id == reviewer_id
            ).all()
            session.expunge_all()
        return groups

    def student_in_group(self, student_id: int, group_id: int) -> bool:
        """Indica si el estudiante esta en el grupo"""
        with self.Session() as session:
            exists_query = (
                select()
                .where(
                    association_table.c.group_id == group_id,
                    association_table.c.student_id == student_id,
                )
                .exists()
            )

            query = select(exists_query)
            result = session.execute(query).scalar()

        return result

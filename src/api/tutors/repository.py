from sqlalchemy.orm import Session, joinedload
from sqlalchemy import exc, exists

from src.api.tutors.models import TutorPeriod
from src.api.periods.exceptions import PeriodDuplicated
from src.api.tutors.exceptions import TutorNotFound, TutorPeriodNotFound
from src.api.topics.exceptions import TopicNotFound
from src.api.topics.models import Topic, TopicTutorPeriod
from src.api.users.models import User, Role


class TutorRepository:

    def __init__(self, sess: Session):
        self.Session = sess

    def is_tutor(self, tutor_id) -> bool:
        with self.Session() as session:
            exists = (
                session.query(User)
                .filter(User.role.in_([Role.TUTOR, Role.ADMIN]))
                .filter(User.id == tutor_id)
                .first()
            )
            return True if exists else False

    def add_tutor_periods(self, tutor_periods: list[TutorPeriod]):
        try:
            with self.Session() as session:
                for period in tutor_periods:
                    session.add(period)
                session.commit()

                for period in tutor_periods:
                    session.refresh(period)
                    session.expunge(period)

            return tutor_periods
        except exc.IntegrityError as e:
            raise PeriodDuplicated(message=f"{e}")

    def add_tutor_period_with_capacity(self, tutor_period: TutorPeriod):
        try:
            with self.Session() as session:
                session.add(tutor_period)
                session.commit()
                session.expunge(tutor_period)

            return tutor_period
        except exc.IntegrityError as e:
            raise PeriodDuplicated(message=f"{e}")

    def get_tutor_by_tutor_id(self, tutor_id) -> User:
        with self.Session() as session:
            tutor = (
                session.query(User)
                .filter(User.id == tutor_id)
                .options(joinedload(User.tutor_periods))
                .first()
            )
            if tutor is None:
                raise TutorNotFound("Tutor doesn't exists")
            session.expunge(tutor)

        return tutor

    def get_tutor_period_by_tutor_email(self, period, tutor_email) -> TutorPeriod:
        with self.Session() as session:
            tutor_period = (
                session.query(TutorPeriod)
                .join(User)
                .filter(User.email == tutor_email, TutorPeriod.period_id == period)
                .one_or_none()
            )

            if tutor_period is None:
                raise TutorNotFound(
                    "The tutor does not exist or this period is not present"
                )

            session.expunge(tutor_period)

        return tutor_period

    def get_tutor_period_by_tutor_id(self, period, tutor_id) -> TutorPeriod:
        with self.Session() as session:
            tutor_period = (
                session.query(TutorPeriod)
                .join(User)
                .filter(User.id == tutor_id, TutorPeriod.period_id == period)
                .one_or_none()
            )

            if tutor_period is None:
                raise TutorNotFound(
                    "The tutor does not exist or this period is not present"
                )

            session.expunge(tutor_period)

        return tutor_period

    def get_tutor_periods_by_periods_id(self, period_id) -> list[TutorPeriod]:
        with self.Session() as session:
            tutor_periods = (
                session.query(TutorPeriod).filter(TutorPeriod.period_id == period_id)
            ).all()

            session.expunge_all()

        return tutor_periods

    def add_topic_tutor_period(
        self,
        period_id: str,
        tutor_email: str,
        topics: list[Topic],
        capacities: list[int],
    ):
        with self.Session() as session:
            topic_tutor_periods = []
            tutor = session.query(User).filter(User.email == tutor_email).first()
            if tutor:
                tutor_period = (
                    session.query(TutorPeriod)
                    .filter(TutorPeriod.tutor_id == tutor.id)
                    .filter(TutorPeriod.period_id == period_id)
                    .one_or_none()
                )
                if tutor_period:
                    for idx, topic in enumerate(topics):
                        topic = (
                            session.query(Topic)
                            .filter(
                                Topic.name == topic.name
                                and Topic.category == topic.category
                            )
                            .first()
                        )
                        topic_tutor_period = TopicTutorPeriod(
                            topic_id=topic.id,
                            tutor_period_id=tutor_period.id,
                            capacity=capacities[idx],
                        )
                        session.add(topic_tutor_period)
                        topic_tutor_periods.append(topic_tutor_period)

                    session.commit()

                    for topic_tutor_period in topic_tutor_periods:
                        session.refresh(topic_tutor_period)
                        session.expunge(topic_tutor_period)

                    return topic_tutor_periods
                raise TutorPeriodNotFound(f"Tutor '{tutor_email}' has no period.")
            raise TutorNotFound(f"Tutor '{tutor_email}' not found.")

    def get_tutors(self):
        with self.Session() as session:
            tutors = (
                session.query(User)
                .filter(User.role.in_([Role.TUTOR, Role.ADMIN]))
                .all()
            )
            session.expunge_all()
        return tutors

    def get_topic_tutor_period(
        self, topic_id: int, tutor_period_id: int
    ) -> TutorPeriod:
        with self.Session() as session:

            topic_exists = session.query(exists().where(Topic.id == topic_id)).scalar()
            if not topic_exists:
                raise TopicNotFound("Topic not found.")

            tutor_period_exists = session.query(
                exists().where(TutorPeriod.id == tutor_period_id)
            ).scalar()
            if not tutor_period_exists:
                raise TutorPeriodNotFound("Tutor period not found.")

            topic_tutor_period = (
                session.query(TopicTutorPeriod)
                .filter(
                    TopicTutorPeriod.topic_id == topic_id,
                    TopicTutorPeriod.tutor_period_id == tutor_period_id,
                )
                .first()
            )
            session.expunge(topic_tutor_period)

        return topic_tutor_period

    def delete_tutor_by_id(self, tutor_id):
        with self.Session() as session:
            tutor = (
                session.query(User)
                .filter(User.role == Role.TUTOR and User.id == tutor_id)
                .first()
            )
            if not tutor:
                raise TutorNotFound(f"Tutor with id: {tutor_id} not exists")

            session.delete(tutor)
            session.commit()

        return tutor

    def delete_tutors_periods_by_period_id(self, period_id):
        with self.Session() as session:
            session.query(TutorPeriod).filter(
                TutorPeriod.period_id == period_id
            ).delete()
            session.commit()

    def get_tutors_by_period_id(self, period_id):
        with self.Session() as session:
            tutors = (
                session.query(User)
                .join(TutorPeriod)
                .filter(TutorPeriod.period_id == period_id)
                .options(joinedload(User.tutor_periods))
                .all()
            )
            session.expunge_all()

        for tutor in tutors:
            tutor.tutor_periods = [
                period
                for period in tutor.tutor_periods
                if period.period_id == period_id
            ]

        return tutors

    def remove_tutor_periods_by_tutor_ids(self, period_id, tutors_ids):
        with self.Session() as session:
            session.query(TutorPeriod).filter(
                TutorPeriod.period_id == period_id
            ).filter(TutorPeriod.tutor_id.in_(tutors_ids)).delete()
            session.commit()

    def add_tutor_period(self, tutor_id, period_id) -> TutorPeriod:
        try:
            with self.Session() as session:
                period_obj = TutorPeriod(period_id=period_id, tutor_id=tutor_id)
                session.add(period_obj)
                session.commit()
                tutor = session.get(User, tutor_id)
                session.expunge_all()

            return tutor
        except exc.IntegrityError:
            raise PeriodDuplicated(message="Period can't be assigned to tutor")

import re

from src.api.auth.hasher import ShaHasher
from src.api.dates.repository import DateSlotRepository
from src.api.exceptions import Duplicated, EntityNotFound
from src.api.groups.repository import GroupRepository
from src.api.periods.exceptions import InvalidPeriod, PeriodDuplicated
from src.api.tutors.schemas import TutorPeriodResponse, TutorRequest, TutorResponse
from src.api.tutors.utils import TutorCsvFile
from src.api.users.models import User, Role
from src.api.tutors.exceptions import (
    TutorNotFound,
    TutorNotInserted,
    TutorPeriodNotInserted,
    TutorDuplicated,
)
from src.api.tutors.models import TutorPeriod
from src.api.users.repository import UserRepository
from src.core.group import AssignedGroup
from src.config.config import api_config


class TutorService:

    def __init__(self, repository) -> None:
        self._repository = repository

    def _make_tutors(self, rows, hasher: ShaHasher):
        """
        Instancia nuevos Usuarios como tutores
        basandose en las filas con la informacion
        necesaria.
        Tambien utiliza el hasher para crear una contraseña cifrada.
        """
        tutors = []
        for i in rows:
            name, last_name, id, email = i
            tutor = User(
                id=int(id),
                name=name,
                last_name=last_name,
                email=email,
                password=hasher.hash(str(id)),
                role=Role.TUTOR,
            )
            tutors.append(tutor)
        return tutors

    def _get_existing_emails(self, tutors_emails):
        tutors = self._repository.get_tutors()
        return [tutor.email for tutor in tutors if tutor.email in tutors_emails]

    def create_tutors_from_csv(
        self, csv: str, period: str, hasher: ShaHasher, user_repository: UserRepository
    ):
        """Con un archivo csv como cadena, crea nuevos tutores y sobrescribe los existentes."""
        try:
            csv_file = TutorCsvFile(csv=csv)
            tutors_emails = csv_file.get_tutors_emails()
            tutors_dtos = csv_file.get_tutors()
            existing_tutors_emails = self._get_existing_emails(tutors_emails)

            remaining_emails = list(
                filter(lambda x: x not in existing_tutors_emails, tutors_emails)
            )

            tutor_periods = []
            tutors = []
            for email in remaining_emails:
                tutor_dto = tutors_dtos[email]
                tutor = User(
                    id=int(tutor_dto.id),
                    name=tutor_dto.name,
                    last_name=tutor_dto.last_name,
                    email=tutor_dto.email,
                    password=hasher.hash(str(tutor_dto.id)),
                    role=Role.TUTOR,
                )
                tutors.append(tutor)

            for email in tutors_emails:
                tutor_dto = tutors_dtos[email]
                tutor_periods.append(
                    TutorPeriod(
                        period_id=period,
                        tutor_id=tutor_dto.id,
                        capacity=tutor_dto.capacity,
                    )
                )

            user_repository.add_tutors(tutors)

            # Clean if the tutor already contains a period asociated
            if len(existing_tutors_emails) > 0:
                ids = [
                    tutor.id
                    for email, tutor in tutors_dtos.items()
                    if email in existing_tutors_emails
                ]
                self._repository.remove_tutor_periods_by_tutor_ids(period, ids)

            # Add new periods
            self._repository.add_tutor_periods(tutor_periods)
            tutors = self._repository.get_tutors_by_period_id(period)

            return tutors
        except TutorDuplicated as e:
            raise Duplicated(str(e))
        except (TutorNotFound, TutorPeriodNotInserted) as e:
            EntityNotFound(str(e))

    def add_tutor(
        self, tutor: TutorRequest, hasher: ShaHasher, userRepository: UserRepository
    ):
        """Crea un tutor y le asocia un cuatrimestre puntual"""
        try:
            tutor_period = TutorPeriod(
                period_id=tutor.period,
                tutor_id=tutor.id,
                capacity=tutor.capacity,
            )

            if not self._repository.is_tutor(tutor.id):
                new_tutor = User(
                    id=tutor.id,
                    name=tutor.name,
                    last_name=tutor.last_name,
                    email=tutor.email,
                    password=hasher.hash(str(tutor.id)),
                    role=Role.TUTOR,
                )
                userRepository.add_user(new_tutor)

            self._repository.add_tutor_period_with_capacity(tutor_period)
            tutor_response = self._repository.get_tutor_by_tutor_id(tutor.id)
            return tutor_response
        except PeriodDuplicated as e:
            raise Duplicated(str(e))
        except Duplicated:
            raise Duplicated("Duplicated tutor")
        except Exception as e:
            print(str(e))
            raise TutorNotInserted("Could not insert a tutor in the database")

    def _validate_period(self, period_id: str):
        """
        Valida que el id del cuatrimestre matchee con el
        patron esperado -> ^[1|2]C20[0-9]{2}$

        Matchea casos donde el cuatrimestre es 1|2C20xx donde xx son numeros 0-9
        """
        regex = re.compile("^[1|2]C20[0-9]{2}$")
        if regex.search(period_id) is not None:
            return True
        else:
            return False

    def add_period_to_tutor(self, tutor_id: int, period_id: str):
        """
        Asigna un tutor a un cuatrimestre dado
        """
        try:
            if self._repository.is_tutor(tutor_id):
                tutor = self._repository.add_tutor_period(tutor_id, period_id)
                return tutor
            else:
                raise EntityNotFound(f"{tutor_id} was not found as TUTOR")
        except PeriodDuplicated as e:
            raise Duplicated(str(e))

    def get_periods_by_tutor_id(self, tutor_id: int):
        """
        Devuelve la lista de periodos
        de un tutor basado en su id.
        """
        try:
            return self._repository.get_tutor_by_tutor_id(tutor_id)
        except TutorNotFound as e:
            raise EntityNotFound(str(e))

    def delete_tutor(self, tutor_id: int):
        """Borra un tutor por id"""
        try:
            return TutorResponse.model_validate(
                self._repository.delete_tutor_by_id(tutor_id)
            )
        except TutorNotFound as e:
            raise EntityNotFound(str(e))

    def get_tutors_by_period_id(self, period_id: str):
        """From a period id, it retrieves all the tutors with their topics"""
        try:
            valid = self._validate_period(period_id)
            if valid:
                tutors = self._repository.get_tutors_by_period_id(period_id)
                return tutors
            else:
                raise InvalidPeriod(
                    message="Period id should follow patter nC20year, ie. 1C2024"
                )
        except PeriodDuplicated as e:
            raise Duplicated(str(e))

    def get_tutor_period_by_tutor_email(self, period: str, tutor_email: str):
        """
        Devuelve un tutor a partir de su email
        """
        try:
            return TutorPeriodResponse.model_validate(
                self._repository.get_tutor_period_by_tutor_email(period, tutor_email)
            )
        except TutorNotFound as e:
            raise EntityNotFound(message=str(e))

    def get_tutor_period_by_tutor_id(self, period: str, tutor_id: int) -> TutorPeriod:
        """
        Devuelve un tutor a partir de su id
        """
        try:
            return self._repository.get_tutor_period_by_tutor_id(period, tutor_id)
        except TutorNotFound as e:
            raise EntityNotFound(message=str(e))

    def get_tutor_periods_by_period_id(self, period_id: str) -> list[TutorPeriod]:
        """Devuelve los cuatrimestres de los tutores a partir de un cuatrimestre puntual"""
        try:
            return self._repository.get_tutor_periods_by_periods_id(period_id)
        except TutorNotFound as e:
            raise EntityNotFound(message=str(e))

    def get_groups_from_tutor_id(
        self, tutor_id: int, period_id: str, group_repository: GroupRepository
    ):
        """Devuelve grupos de un tutor"""
        period = self.get_tutor_period_by_tutor_id(period_id, tutor_id)
        groups = group_repository.get_groups_by_period_id(
            tutor_period_id=period.id, load_topic=True
        )
        return groups

    def get_groups_from_reviewer_id(
        self, reviewer_id: int, period_id: str, group_repository: GroupRepository
    ):
        """Devuelve los grupos de un revisor"""
        try:
            groups = group_repository.get_groups_by_reviewer_id(
                reviewer_id=reviewer_id, period_id=period_id, load_topic=True
            )
            return groups
        except Exception as e:
            raise EntityNotFound(message=str(e))

    def notify_students(
        self, sender_id: int, group: AssignedGroup, email_sender: object, message: str
    ):
        """Envia un mail a los alumnos de un grupo con copia al admin"""
        try:
            sender = self._repository.get_tutor_by_tutor_id(sender_id)
            to = group.emails()

            if group.reviewer_id and sender.id == group.reviewer_id:
                tutor = self._repository.get_tutor_by_tutor_id(group.tutor_id())
                to.extend([tutor.email, sender.email])
                subject = "Tienes un nuevo mensaje de tu revisor"
            else:
                to.append(sender.email)
                subject = "Tienes un nuevo mensaje de tu tutor"

            body = f"Mensaje:\n\n{message}\n\nGracias"
            cc = api_config.cc_emails
            response = email_sender.send_emails(
                to=to, subject=subject, body=body, cc=cc
            )

            return response
        except Exception as e:
            raise EntityNotFound(message=str(e))

    def get_tutors_with_dates(self, period_id: str):
        """Devuelve los tutores con las fechas cargadas"""
        try:
            tutors = self._repository.get_tutors_by_period_id_with_available_dates(
                period_id=period_id
            )
            return tutors
        except PeriodDuplicated as e:
            raise Duplicated(str(e))

    def get_evaluators_with_dates(self, period_id: str):
        """Devuelve los evaluadores con las fechas cargadas"""
        try:
            valid = self._validate_period(period_id)
            if valid:
                evaluators = (
                    self._repository.get_evaluators_by_period_id_with_available_dates(
                        period_id=period_id, is_evaluator=True
                    )
                )
                return evaluators
            else:
                raise InvalidPeriod(
                    message="Period id should follow patter nC20year, ie. 1C2024"
                )
        except PeriodDuplicated as e:
            raise Duplicated(str(e))

    def get_assigned_dates(
        self, period_id: str, tutor_id: int, dates_repository: DateSlotRepository
    ):
        """Devuelve una tupla con las fechas asignadas como tutor y como evaluador"""
        dates = dates_repository.get_tutors_assigned_dates(tutor_id, period_id)
        tutor_dates = list(filter(lambda x: x[0].tutor_or_evaluator == "tutor", dates))
        evaluators_dates = list(
            filter(lambda x: x[0].tutor_or_evaluator == "evaluator", dates)
        )

        return (tutor_dates, evaluators_dates)

    def make_evaluator(self, period_id, tutor_id):
        """Hace evaluador a un tutor en un cuatrimestre dado"""
        self._repository.update_tutor_period(
            period_id, tutor_id, {"is_evaluator": True}
        )

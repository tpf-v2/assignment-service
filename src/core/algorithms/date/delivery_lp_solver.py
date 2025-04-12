import pyscipopt as scip
from src.constants import DATE_ID, EVALUATOR_ID, GROUP_ID, TUTOR_ID
from src.core.date_slots import DateSlot
from src.core.delivery_date import DeliveryDate
from src.core.group import AssignedGroup
from src.core.result import DateSlotAssignment, DateSlotsAssignmentResult
from src.core.tutor import Tutor

GROUP = 0
TUTOR = 1
EVALUATOR = 2
WEEK = 3
DAY = 4
HOUR = 5


class DeliveryLPSolver:
    """
    Clase para resolver el problema de asignar evaluadores a grupos
    utilizando programación lineal.

    Attributes:
    -----------
    _evaluators : list
        Lista de evaluadores disponibles.
    _decision_variables : dict
        Variables de decisión para la asignación.
    _evaluator_day_vars : dict
        Variables para minimizar los días de asistencia de los evaluadores.
    _model : scip.Model
        Modelo SCIP para resolver el problema.
    """

    def __init__(
        self,
        groups: list[AssignedGroup] = [],
        tutors: list[Tutor] = [],
        evaluators: list[Tutor] = [],
        available_dates: list[DateSlot] = [],
        max_groups_per_week: int = 5,
        max_dif_evaluators: int = 5,
    ):
        """
        Inicializa la clase con los períodos de tutores y fechas.

        Parameters:
        -----------
        available_dates : list
            Lista de fechas disponibles.
        tutor_periods : list
            Lista de tutores.
        """

        self._evaluators = evaluators
        self._tutors = tutors
        self._groups = groups
        self._available_dates = available_dates
        self._decision_variables = {}
        self._evaluator_day_vars = {}
        self._model = scip.Model()
        self._model.setIntParam("display/verblevel", 0)
        self.max_groups_per_week = max_groups_per_week
        self.max_dif_evaluators = max_dif_evaluators

    def create_decision_variables(self):
        """
        Crea variables de decisión para la asignación de evaluadores a grupos.

        Esta función itera sobre cada grupo y evaluador, determinando las
        fechas posibles en las que el grupo y sus tutores pueden reunirse con el evaluador.
        Para cada combinación válida de grupo, tutor, evaluador y fecha, se
        crea una variable de decisión para representar si el evaluador está asignado
        al grupo en esa fecha.
        """
        for tutor in self._tutors:
            # Verificar si el tutor tiene fechas en común con algún evaluador
            has_common_dates = any(
                any(t_date.date == e_date.date for t_date in tutor.available_dates)
                for evaluator in self._evaluators
                for e_date in evaluator.available_dates
            )

            # Si no hay fechas en común, asignar todas las fechas disponibles al tutor
            if not has_common_dates:
                tutor.available_dates = self._available_dates

            for group in self._groups:
                if group.tutor_id() == tutor.id:
                    if group.available_dates:

                        group_tutor_possible_dates = self._find_common_dates(
                            group, tutor
                        )
                        if group_tutor_possible_dates:
                            for evaluator in self._evaluators:
                                self._create_evaluator_decision_variables(
                                    group, tutor, evaluator, group_tutor_possible_dates
                                )

    def _find_common_dates(self, group: AssignedGroup, tutor: Tutor):
        """
        Encuentra fechas comunes disponibles para todos los tutores en el grupo.

        Parameters:
        -----------
        group : Group
            El grupo que necesita un evaluador.
        tutor : TutorPeriod
            El tutor asociado con el grupo.

        Returns:
        --------
        list
            Lista de tuplas que representan fechas comunes (semana, día, hora).
        """

        return [
            (g_date.get_week(), g_date.get_day_of_week(), g_date.get_hour())
            for g_date in group.available_dates
            if any(t_date.date == g_date.date for t_date in tutor.available_dates)
        ]

    def _create_evaluator_decision_variables(
        self,
        group: AssignedGroup,
        tutor: Tutor,
        evaluator: Tutor,
        group_tutor_possible_dates: list[tuple[int, int, int]],
    ):
        """
        Crea variables de decisión para las posibles asignaciones de un evaluador.

        Para cada combinación de grupo, evaluador y fecha posible, crea
        variables de decisión que indican si el evaluador está asignado al
        grupo en esa fecha. También crea variables de día para los evaluadores y
        tutores para rastrear los días en los que están asignados.

        Parameters:
        -----------
        group : Group
            El grupo que necesita un evaluador.
        tutor : TutorPeriod
            El tutor asociado con el grupo.
        evaluator : Evaluator
            El evaluador considerado para la asignación.
        group_tutors_possible_dates : list
            Lista de fechas (semana, día, hora) en las que el grupo y los tutores pueden reunirse.
        """

        if evaluator.id != tutor.id:
            group_tutor_evaluator_possible_dates = [
                (week, day, hour)
                for (week, day, hour) in group_tutor_possible_dates
                for e_date in evaluator.available_dates
                if day == e_date.get_day_of_week()
                and week == e_date.get_week()
                and hour == e_date.get_hour()
            ]
            if group_tutor_evaluator_possible_dates:
                for week, day, hour in group_tutor_evaluator_possible_dates:
                    self._create_decision_variable(
                        group, tutor.id, evaluator, week, day, hour
                    )
                    self._create_evaluator_day_variable(evaluator, week, day)

    def _create_decision_variable(
        self,
        group: AssignedGroup,
        tutor_id: int,
        evaluator: Tutor,
        week: int,
        day: int,
        hour: int,
    ):
        """
        Crea una única variable de decisión para una asignación específica.

        Esta función crea una variable de decisión binaria que indica si un
        evaluador particular está asignado a un grupo en una fecha específica.

        Parameters:
        -----------
        group : Group
            El grupo que necesita un evaluador.
        tutor_id : int
            ID del tutor asociado con el grupo.
        evaluator : TutorPeriod
            El evaluador considerado para la asignación.
        week : int
            El número de semana de la asignación.
        day : int
            El día de la semana de la asignación.
        hour : int
            La hora del día de la asignación.
        """

        var_name = f"{GROUP_ID}-{group.id}-{TUTOR_ID}-{tutor_id}-{EVALUATOR_ID}-{evaluator.id}-{DATE_ID}-{week}-{day}-{hour}"
        self._decision_variables[
            (group.id, tutor_id, evaluator.id, week, day, hour)
        ] = self._model.addVar(var_name, vtype="B", obj=0, lb=0, ub=1)

    def _create_evaluator_day_variable(self, evaluator, week, day):
        """
        Crea una variable de día para un evaluador.

        Esta función crea una variable binaria que indica si un evaluador
        está asignado a algún grupo en un día específico.

        Parameters:
        -----------
        evaluator : Evaluator
            El evaluador considerado.
        week : int
            El número de semana de la asignación.
        day : int
            El día de la semana de la asignación.
        """

        if (evaluator.id, week, day) not in self._evaluator_day_vars:
            day_var_name = f"{EVALUATOR_ID}-{evaluator.id}-{DATE_ID}-{week}-{day}"
            self._evaluator_day_vars[(evaluator.id, week, day)] = self._model.addVar(
                day_var_name, vtype="B", obj=0, lb=0, ub=1
            )

    def add_group_assignment_constraints(self):
        """
        Agrega restricciones de asignación de grupos al modelo.
        """

        for tutor in self._tutors:
            for group in self._groups:
                if group.tutor_id() == tutor.id:
                    self._add_unique_date_constraint(group, tutor)
                    self._add_assignment_constraints(group)

    def _add_unique_date_constraint(self, group, tutor):
        """
        Agrega una restricción para asegurar que cada grupo esté asignado a una fecha única.
        Variables de fecha única del grupo: group-id-date-week-day-hour

        Parameters:
        -----------
        group : Group
            Un grupo que necesita un evaluador.
        """

        group_possible_dates = [
            (week, day, hour)
            for (g, _, _, week, day, hour) in self._decision_variables
            if g == group.id
        ]
        if group_possible_dates:
            group_date_vars = self._create_group_date_variables(
                group, group_possible_dates, tutor
            )
            self._model.addCons(
                scip.quicksum(group_date_vars.values()) == 1,
                name=f"{GROUP_ID}-{group.id}",
            )

    def _create_group_date_variables(self, group, group_possible_dates, tutor):
        """
        Crea variables de fecha para un grupo.

        Esta función crea variables binarias para cada fecha posible
        a la que un grupo puede ser asignado para asegurar que sean mutuamente exclusivas.

        Parameters:
        -----------
        group : Group
            El grupo que necesita un evaluador.
        group_possible_dates : list
            Lista de fechas posibles (semana, día, hora) para el grupo.
        tutor : TutorPeriod
            El tutor asociado con el grupo.

        Returns:
        --------
        dict
            Diccionario de variables de fecha creadas.
        """

        group_date_vars = {}
        for date in group_possible_dates:
            group_date_var = self._model.addVar(
                f"{GROUP_ID}-{group.id}-{DATE_ID}-{date[0]}-{date[1]}-{date[2]}",
                vtype="B",
                obj=0,
                lb=0,
                ub=1,
            )
            group_date_vars[date] = group_date_var
            self._model.addCons(
                group_date_var
                >= scip.quicksum(
                    self._decision_variables[
                        (
                            group.id,
                            tutor.id,
                            evaluator.id,
                            date[0],
                            date[1],
                            date[2],
                        )
                    ]
                    for evaluator in self._evaluators
                    if (
                        group.id,
                        tutor.id,
                        evaluator.id,
                        date[0],
                        date[1],
                        date[2],
                    )
                    in self._decision_variables
                )
                / len(self._evaluators),
                name=f"{GROUP_ID}-{group.id}-{DATE_ID}-{date[0]}-{date[1]}-{date[2]}",
            )
        return group_date_vars

    def _add_assignment_constraints(self, group):
        """
        Agrega restricciones para asegurar que cada grupo esté asignado a un solo evaluador.

        Parameters:
        -----------
        group : Group
            Un grupo que necesita un evaluador.
        """

        variables = [
            self._decision_variables[var]
            for var in self._decision_variables
            if var[GROUP] == group.id
        ]
        if variables:
            self._model.addCons(
                scip.quicksum(variables) == 1,
                name=f"min-assign-{GROUP_ID}-{group.id}",
            )

    def add_unique_group_per_date_constraint(self):
        """
        Agrega la restricción de que cada fecha puede tener solo un grupo asignado.
        """

        dates = set(
            (week, day, hour) for _, _, _, week, day, hour in self._decision_variables
        )
        for date in dates:
            variables = [
                self._decision_variables[var]
                for var in self._decision_variables
                if (var[WEEK], var[DAY], var[HOUR]) == date
            ]
            if variables:
                self._model.addCons(
                    scip.quicksum(variables) <= 1, name=f"unique-group-date-{date}"
                )

    def add_evaluator_minimization_constraints(self):
        """
        Agrega restricciones para minimizar los días de asistencia de los evaluadores.
        """

        for evaluator_id, week, day in self._evaluator_day_vars:
            self._model.addCons(
                self._evaluator_day_vars[(evaluator_id, week, day)]
                >= scip.quicksum(
                    self._decision_variables[var]
                    for var in self._decision_variables
                    if var[EVALUATOR] == evaluator_id
                    and var[WEEK] == week
                    and var[DAY] == day
                )
                / len(self._available_dates)
            )

    def add_evaluator_group_assignment_constraints(self):
        """
        Agrega restricciones para asegurar que los evaluadores estén asignados a todos
        los grupos presentes en un día dado, hasta un máximo de 5 grupos por semana.
        """

        for evaluator in self._evaluators:
            self._add_weekly_group_limit_constraint(evaluator)

    def _add_weekly_group_limit_constraint(self, evaluator: Tutor):
        """
        Agrega una restricción para limitar el número de grupos asignados a
        un evaluador por semana.

        Parameters:
        -----------
        evaluator : Evaluator
            Un evaluador disponible para la asignación.
        """

        weeks = set(date.get_week() for date in self._available_dates)
        for week in weeks:
            self._model.addCons(
                scip.quicksum(
                    self._decision_variables[var]
                    for var in self._decision_variables
                    if var[EVALUATOR] == evaluator.id and var[WEEK] == week
                )
                <= self.max_groups_per_week,
                name=f"max-10-groups-week-{EVALUATOR_ID}-{evaluator.id}-{week}",
            )

    def define_objective(self):
        """
        Define el objetivo de minimizar el número de días
        en que los evaluadores y tutores asisten.
        """

        self._model.setObjective(
            scip.quicksum(
                week * self._evaluator_day_vars[(evaluator_id, week, day)]
                for (evaluator_id, week, day) in self._evaluator_day_vars
            ),
            "minimize",
        )

    def create_auxiliary_variables(self):
        """
        Crea variables auxiliares para el número de asignaciones por evaluador.
        """

        self._evaluator_assignment_vars = {}
        for evaluator in self._evaluators:
            var_name = f"{EVALUATOR_ID}-{evaluator.id}-assignments"
            self._evaluator_assignment_vars[evaluator.id] = self._model.addVar(
                var_name, vtype="I", obj=0, lb=0
            )

    def add_assignment_count_constraints(self):
        """
        Agrega restricciones para contar el número de asignaciones por evaluador.
        """

        for evaluator in self._evaluators:
            self._model.addCons(
                self._evaluator_assignment_vars[evaluator.id]
                == scip.quicksum(
                    self._decision_variables[var]
                    for var in self._decision_variables
                    if var[EVALUATOR] == evaluator.id
                ),
                name=f"count-assignments-{EVALUATOR_ID}-{evaluator.id}",
            )

    def add_balance_constraints(self):
        """
        Agrega restricciones para equilibrar la carga de trabajo entre los evaluadores.
        """

        for i, evaluator_i in enumerate(self._evaluators):
            for j, evaluator_j in enumerate(self._evaluators):
                if i < j:
                    self._model.addCons(
                        self._evaluator_assignment_vars[evaluator_i.id]
                        - self._evaluator_assignment_vars[evaluator_j.id]
                        <= self.max_dif_evaluators,  # Balance threshold
                        name=f"balance-{EVALUATOR_ID}-{evaluator_i.id}\
                            -{evaluator_j.id}",
                    )
                    self._model.addCons(
                        self._evaluator_assignment_vars[evaluator_j.id]
                        - self._evaluator_assignment_vars[evaluator_i.id]
                        <= self.max_dif_evaluators,  # Balance threshold
                        name=f"balance-{EVALUATOR_ID}-{evaluator_j.id}-\
                            {evaluator_i.id}",
                    )

    def _find_substitutes_on_date(self, date, evaluator_id, tutor_id):
        substitutes = []
        for evaluator in self._evaluators:
            if (
                evaluator.is_avaliable(date.label())
                and evaluator.id != evaluator_id
                and evaluator.id != tutor_id
            ):
                substitutes.append(evaluator.id)
                evaluator.add_substitute_date(date)

        return substitutes

    def solve(self):
        """
        Resuelve el modelo de programación lineal.

        Returns:
        --------
        list
            Lista de variables de decisión activadas.
        """
        self.create_decision_variables()
        self.create_auxiliary_variables()

        self.add_group_assignment_constraints()
        self.add_evaluator_minimization_constraints()
        self.add_evaluator_group_assignment_constraints()
        self.add_unique_group_per_date_constraint()
        self.add_assignment_count_constraints()
        self.add_balance_constraints()
        self.define_objective()
        self._model.optimize()

        results = DateSlotsAssignmentResult(status=-1, assignments=[])
        if self._model.getStatus() == "optimal":
            return self._get_results(results)

        return results

    def _get_results(self, results: DateSlotsAssignmentResult):
        """
        Recupera e imprime los resultados del solucionador.

        Returns:
        --------
        list
            Lista de variables de decisión activadas.
        """

        rounded_decision_vars = {
            var: round(self._model.getVal(self._decision_variables[var]))
            for var in self._decision_variables
        }

        results.status = 1
        for var in rounded_decision_vars:
            if rounded_decision_vars[var] > 0:
                group_id, tutor_id, evaluator_id, week, day, hour = var
                date = next(
                    dt
                    for dt in self._available_dates
                    if dt.is_same_date(week, day, hour)
                )
                group_number = next(
                    (
                        group.group_number
                        for group in self._groups
                        if group.id == group_id
                    ),
                    0,
                )
                assignment = DateSlotAssignment(
                    group_id=group_id,
                    group_number=group_number,
                    tutor_id=tutor_id,
                    evaluator_id=evaluator_id,
                    date=date,
                )
                results.add_assignment(assignment)

        return results

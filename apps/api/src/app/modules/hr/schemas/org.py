"""D01 Organization DTOs — M1.2 EP-ORG-01..24 (10 §7.2.1, 05 §2.4). No level 3/4 fields."""

import uuid
from datetime import date

from pydantic import BaseModel, Field

from app.modules.hr.schemas import _Out, _Patch

Code = Field(min_length=1, max_length=50)
Name = Field(min_length=1, max_length=200)


# ---------- EP-ORG-01..05 organizations ----------
class OrganizationCreate(BaseModel):
    code: str = Code
    name: str = Name
    legal_name: str | None = Field(default=None, max_length=300)
    tax_code: str | None = Field(default=None, max_length=20)
    valid_from: date | None = None


class OrganizationUpdate(_Patch):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    legal_name: str | None = Field(default=None, max_length=300)
    tax_code: str | None = Field(default=None, max_length=20)


class OrganizationOut(_Out):
    code: str
    name: str
    legal_name: str | None
    tax_code: str | None
    valid_from: date
    valid_to: date | None


# ---------- EP-ORG-11..15 teams ----------
class TeamCreate(BaseModel):
    department_id: uuid.UUID
    code: str = Code
    name: str = Name
    lead_employee_id: uuid.UUID | None = None
    valid_from: date | None = None


class TeamUpdate(_Patch):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    lead_employee_id: uuid.UUID | None = None


class TeamOut(_Out):
    department_id: uuid.UUID
    code: str
    name: str
    lead_employee_id: uuid.UUID | None
    valid_from: date
    valid_to: date | None


# ---------- EP-ORG-16..20 positions ----------
class PositionCreate(BaseModel):
    department_id: uuid.UUID
    code: str = Code
    title: str = Name
    level: int | None = Field(default=None, ge=0, le=32767)
    headcount_budget: int = Field(ge=0, le=32767)
    reports_to_position_id: uuid.UUID | None = None


class PositionUpdate(_Patch):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    level: int | None = Field(default=None, ge=0, le=32767)
    headcount_budget: int | None = Field(default=None, ge=0, le=32767)
    reports_to_position_id: uuid.UUID | None = None


class PositionOut(_Out):
    department_id: uuid.UUID
    code: str
    title: str
    level: int | None
    headcount_budget: int
    reports_to_position_id: uuid.UUID | None
    filled: int
    vacant: int


# ---------- EP-ORG-21..23 assignments ----------
class AssignmentCreate(BaseModel):
    employee_id: uuid.UUID
    department_id: uuid.UUID
    team_id: uuid.UUID | None = None
    position_id: uuid.UUID | None = None
    manager_id: uuid.UUID | None = None
    valid_from: date
    reason: str | None = Field(default=None, max_length=500)


class AssignmentUpdate(_Patch):
    reason: str | None = Field(default=None, max_length=500)
    manager_id: uuid.UUID | None = None
    valid_to: date | None = None


class EmployeeAssignmentOut(_Out):
    employee_id: uuid.UUID
    department_id: uuid.UUID
    team_id: uuid.UUID | None
    position_id: uuid.UUID | None
    manager_id: uuid.UUID | None
    valid_from: date
    valid_to: date | None
    reason: str | None


# ---------- EP-ORG-24 tree ----------
class TreeTeam(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    lead_employee_id: uuid.UUID | None
    headcount: int


class TreeMember(BaseModel):
    employee_id: uuid.UUID
    employee_code: str
    full_name: str
    team_id: uuid.UUID | None
    position_id: uuid.UUID | None
    position_title: str | None
    manager_id: uuid.UUID | None


class TreeDepartment(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    parent_id: uuid.UUID | None
    manager_id: uuid.UUID | None
    headcount: int
    teams: list[TreeTeam]
    members: list[TreeMember]


class TreeOrganization(BaseModel):
    id: uuid.UUID
    code: str
    name: str


class OrgTreeOut(BaseModel):
    as_of: date
    organization: TreeOrganization
    departments: list[TreeDepartment]

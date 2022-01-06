import enum
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field, validator

from . import base, constants
from .validated_types import StrictIntFlag


class RoleFlagsType(StrictIntFlag):
    IsMirror = 1
    IsPremiseAggregationPoint = 2
    IsPEV = 4
    IsDER = 8
    IsRevenueQuality = 16
    IsDC = 32
    IsSubmeter = 64


class ServiceKind(enum.IntEnum):
    Electricity = 0
    Gas = 1
    Water = 2
    Time = 3
    Pressure = 4
    Heat = 5
    Cooling = 6


class MirrorUsagePoint(BaseModel):
    xmlns: str = Field(alias="@xmlns", default="urn:ieee:std:2030.5:ns")
    href: str = Field(alias="@href", default="")
    mrid: base.mRIDType = Field(alias="mRID")
    description: Optional[str] = Field()
    role_flags: RoleFlagsType = Field(alias="roleFlags")
    service_category_kind: ServiceKind = Field(alias="serviceCategoryKind")
    status: int = Field()
    device_lfdi: str = Field(alias="deviceLFDI")

    class XmlTemplate:
        create = {
            "by_alias": True,
        }


class MirrorUsagePointList(base.PydanticList):
    """A List element to hold `MirrorUsagePoint` objects."""

    # Can't tell the difference between single item and list in XML, so need to cater to
    # single item entry
    mirror_usage_point: Union[List[MirrorUsagePoint], MirrorUsagePoint] = Field(
        alias="MirrorUsagePoint"
    )
    list_field: Literal["mirror_usage_point"] = "mirror_usage_point"

    @validator("mirror_usage_point")
    def ensure_list(cls, v):
        if not isinstance(v, list):
            return [v]
        return v


# p212
class ReadingType(BaseModel):
    accumulation_behaviour: Optional[constants.AccumulationBehaviourType] = Field(
        alias="accumulationBehaviour"
    )
    calorific_value: Optional[base.UnitValueType] = Field(alias="calorificValue")
    commodity: Optional[constants.CommodityType] = Field(alias="commodity")
    conversion_factor: Optional[base.UnitValueType] = Field(alias="conversionFactor")
    data_qualifier: Optional[constants.DataQualifierType] = Field(alias="dataQualifier")
    flow_direction: Optional[constants.FlowDirectionType] = Field(alias="flowDirection")
    interval_length: Optional[int] = Field(alias="intervalLength")
    kind: Optional[constants.KindType] = Field(alias="kind")
    max_number_of_intervals: Optional[int] = Field(alias="maxNumberOfIntervals")
    number_of_consumption_blocks: Optional[int] = Field(
        alias="numberOfConsumptionBlocks"
    )
    number_of_tou_tiers: Optional[int] = Field(alias="numberOfTouTiers")
    phase: Optional[constants.PhaseCode] = Field(alias="phase")
    power_of_ten_multiplier: Optional[base.PowerOfTenMultiplierType] = Field(
        alias="powerOfTenMultiplier"
    )
    sub_interval_length: Optional[int] = Field(alias="subIntervalLength")
    supply_limit: Optional[int] = Field(alias="supplyLimit")
    tiered_consumption_blocks: Optional[bool] = Field(alias="tieredConsumptionBlocks")
    uom: Optional[constants.UomType] = Field(alias="uom")

    class XmlTemplate:
        create = {
            "by_alias": True,
            "exclude_unset": True,
        }


""" Mirror Usage Point related
"""


# p216
class ReadingBase(base.Resource):
    consumption_block: Optional[constants.ConsumptionBlockType] = Field(
        alias="consumptionBlock"
    )
    quality_flags: Optional[constants.QualityFlagsType] = Field(alias="qualityFlags")
    time_period: Optional[base.DateTimeIntervalType] = Field(alias="timePeriod")
    tou_tier: Optional[constants.TOUType] = Field(alias="touTier")
    value: Optional[int]

    class XmlTemplate:
        create = {
            "by_alias": True,
            "exclude_unset": True,
        }


# p211
class Reading(ReadingBase):
    local_id: Optional[int] = Field(alias="localID")
    subscribable: Optional[constants.SubscribableType]

    class XmlTemplate:
        create = {
            "by_alias": True,
        }

    class Config:
        fields = {"subscribable": "@subscribable"}


# p217
class ReadingSetBase(base.IdentifiedObject):
    time_period: base.DateTimeIntervalType = Field(alias="timePeriod")

    class XmlTemplate:
        create = {
            "by_alias": True,
        }


class MeterReadingBase(base.IdentifiedObject):
    pass


class MirrorReadingSet(ReadingSetBase):
    reading: List[Reading] = Field(alias="Reading")

    class XmlTemplate:
        create = {
            "by_alias": True,
        }


# p215
class MirrorMeterReading(base.IdentifiedObject):
    last_update_time: Optional[base.TimeType] = Field(alias="lastUpdateTime")
    next_update_time: Optional[base.TimeType] = Field(alias="nextUpdateTime")
    reading_type: Optional[ReadingType] = Field(alias="ReadingType")
    mirror_reading_set: Union[List[MirrorReadingSet], MirrorReadingSet, None] = Field(
        alias="MirrorReadingSet"
    )
    reading: Optional[Reading] = Field(alias="Reading")

    class XmlTemplate:
        create = {
            "by_alias": True,
            "exclude_unset": True,
        }

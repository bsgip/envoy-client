
from .constants import *
from .base import *
from typing import Optional
import enum

class RoleFlagsType(enum.Flag):
    IsMirror = 0
    IsPremiseAggregationPoint = 1
    IsPEV = 2
    IsDER = 4
    IsRevenueQuality = 8
    IsDC = 16
    IsSubmeter = 32


class ServiceKind(enum.IntEnum):
    Electricity = 0
    Gas = 1
    Water = 2
    Time = 3
    Pressure = 4
    Heat = 5
    Cooling = 6


class MirrorUsagePoint(BaseModel):
    mrid: str = Field(alias="mRID")
    description: Optional[str] = Field()
    role_flags: RoleFlagsType = Field(alias="roleFlags")
    service_category_kind: ServiceKind = Field(alias="serviceCategoryKind")
    status: int = Field()
    device_lfdi: str = Field(alias="deviceLFDI")

# p212
class ReadingType(BaseModel):
    accumulation_behaviour: Optional[AccumlationBehaviourType] = Field(alias="accumulationBehaviour")
    calorific_value: Optional[UnitValueType] = Field(alias="calorificValue")
    commodity: Optional[CommodityType] = Field(alias="commodity")
    conversion_factor: Optional[UnitValueType] = Field(alias="conversionFactor")
    data_qualifier: Optional[DataQualifierType] = Field(alias="dataQualifier")
    flow_direction: Optional[FlowDirectionType] = Field(alias="flowDirection")
    interval_length: Optional[int] = Field(alias="intervalLength")
    kind: Optional[KindType] = Field(alias="kind")
    max_number_of_intervals: Optional[int] = Field(alias="maxNumberOfIntervals")
    number_of_consumption_blocks: Optional[int] = Field(alias="numberOfConsumptionBlocks")
    number_of_tou_tiers: Optional[int] = Field(alias="numberOfTouTiers")
    phase: Optional[PhaseCode] = Field(alias="phase")
    power_of_ten_multiplier: Optional[PowerOfTenMultiplierType] = Field(alias="powerOfTenMultiplier")
    sub_interval_length: Optional[int] = Field(alias="subIntervalLength")
    supply_limit: Optional[int] = Field(alias="supplyLimit")
    tiered_consumption_blocks: Optional[bool] = Field(alias="tieredConsumptionBlocks")
    uom: Optional[UomType] = Field(alias="uom")


""" Mirror Usage Point related
"""
# p216
class ReadingBase(Resource):
    consumption_block: Optional[ConsumptionBlockType] = Field(alias="consumptionBlock")
    quality_flags: Optional[QualityFlagsType] = Field(alias="qualityFlags")
    time_period: Optional[DateTimeIntervalType] = Field(alias="timePeriod")
    tou_tier: Optional[TOUType] = Field(alias="touTier")
    value: Optional[int]


# p211
class Reading(ReadingBase):
    local_id: Optional[int] = Field(alias="localID")
    subscribable: Optional[SubscribableType]

    class Config:
        fields = {
            'subscribable': '@subscribable'
        }


# p217
class ReadingSetBase(IdentifiedObject):
    time_period: DateTimeIntervalType = Field(alias="timePeriod")


class MeterReadingBase(IdentifiedObject):
    pass


class MirrorReadingSet(ReadingSetBase):
    reading: List[Reading] = Field(alias="Reading")

    

# p215
class MirrorMeterReading(IdentifiedObject):
    last_update_time: Optional[TimeType] = Field(alias="lastUpdateTime")
    next_update_time: Optional[TimeType] = Field(alias="nextUpdateTime")
    reading_type: Optional[ReadingType] = Field(alias="ReadingType")
    mirror_reading_set: Union[List[MirrorReadingSet], MirrorReadingSet, None] = Field(alias="MirrorReadingSet")
    reading: Optional[Reading] = Field(alias="Reading")
 
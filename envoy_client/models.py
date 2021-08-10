from pydantic import BaseModel, Field, validator
from typing import List, Literal, Optional
import enum

class PydanticList(BaseModel):
    list_field: Literal["None"] = "None"

    def dict(self, *args, **kwargs):
        include, exclude = None, None
        if 'include' in kwargs:
            kwargs['include'] = kwargs['include'].get(self.list_field)
        if 'exclude' in kwargs:
            print(kwargs['exclude'])
            print(self.list_field)
            exclude = kwargs['exclude']
            if isinstance(exclude, set) and self.list_field in exclude:
                return []
            else:
                kwargs['exclude'] = exclude.get(self.list_field)


        return {self.__class__.__name__: [
            {(self.__fields__[self.list_field].alias or self.list_field): sub.dict(*args, **kwargs)} for sub in getattr(self, self.list_field)
        ]}

class DeviceCategoryType(enum.IntEnum):
    electric_vehicle = 65536
    virtual_or_mixed_der = 262144
    reciprocating_engine = 524288
    photovoltaic_system = 2097152
    combined_pv_and_storage = 8388608
    other_generation_system = 16777216
    other_storage_system = 33554432



class ActivePower(BaseModel):
    multipler: int = 0
    value: float = Field()


class Link(BaseModel):
    href: str = Field(default=None, alias='@href')


class DeviceInformation(BaseModel):
    pass

class DERCapability(BaseModel):
    modes_supported: int = Field(default=1, alias='modesSupported')
    rtgMaxW: float = Field()
    type_: int = Field(alias='type')

class DER(BaseModel):
    der_capability: DERCapability = Field(alias='DERCapability')


class EndDevice(BaseModel):
    device_category: DeviceCategoryType = Field(alias='deviceCategory') # TODO Actually use enum values
    lfdi: str = Field(alias='lFDI')
    sfdi: str = Field(alias='sFDI')
    der_list_link: Optional[Link] = Field(default=None, alias="DERListLink")
    device_information_link: Optional[Link] = Field(default=None, alias="DeviceInformationLink")
    der: Optional[List[DER]] = Field()
    device_information: Optional[DeviceInformation] = Field()

    class Config:
        use_enum_values = True


    # @validator('device_category')
    # def to_int(cls, v):
    #     print(v)
    #     return int(v)


class EndDeviceList(PydanticList):
    end_device: List[EndDevice] = Field(alias='EndDevice')
    list_field: Literal["end_device"] = "end_device"

    @validator('end_device')
    def ensure_list(cls, v):
        if not isinstance(v, list):
            return [v]
        return v

    # def dict(self, *args, **kwargs):
    #     return {'EndDeviceList': super().dict(*args, **kwargs)}


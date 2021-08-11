from pydantic import BaseModel as PydanticBaseModel, Field, validator
from typing import List, Literal, Optional, Union
import enum
import xmltodict


END_DEVICE_CREATE_TEMPLATE_KWARGS = {
    'include': {'device_category', 'lfdi', 'sfdi'},
    'by_alias': True
}

DER_CREATE_TEMPLATE = {
    'include': {}
}

DER_CAPABILITY_CREATE_TEMPLATE = {
    'include': {'modes_supported', 'rtg_max_w', 'type_'},
    'by_alias': True
}

DEVICE_INFORMATION_CREATE_TEMPLATE = {
    'include': {}
}

class BaseModel(PydanticBaseModel):
    class Config:
        allow_population_by_field_name = True

    class XmlTemplate:
        create = {}
        link = {}
        show = {}

    def dict(self, *args, **kwargs):
        if 'mode' in kwargs:
            additional_kwargs = getattr(self.XmlTemplate, kwargs.pop('mode'), {})
            return super().dict(*args, **{**kwargs, **additional_kwargs})
        return super().dict(*args, **kwargs)

    def xml_dict(self, *args, **kwargs):
        return {self.__class__.__name__: self.dict(*args, **kwargs)}

    @classmethod
    def from_xml(cls, document):
        return cls(**xmltodict.parse(document)[cls.__name__])

    def to_xml(self, mode='create', pretty=False):
        return xmltodict.unparse(self.xml_dict(mode=mode), full_document=False, pretty=pretty)




class PydanticList(BaseModel):
    list_field: Literal["None"] = "None"

    def dict(self, *args, **kwargs):
        include, exclude = None, None
        if 'include' in kwargs:
            include = kwargs['include']
            if isinstance(include, set):
                kwargs['include'] = None
        if 'exclude' in kwargs:
            print(kwargs['exclude'])
            print(self.list_field)
            exclude = kwargs['exclude']
            if isinstance(exclude, set) and self.list_field in exclude:
                return []
            elif isinstance(exclude, dict):
                kwargs['exclude'] = exclude.get(self.list_field)
            else:
                kwargs['exclude'] = None


        return {self.__class__.__name__: 
            {
                (self.__fields__[self.list_field].alias or self.list_field): 
                [sub.dict(*args, **kwargs) for sub in getattr(self, self.list_field)]
            }
        }

    def xml_dict(self, *args, **kwargs):
        return self.dict(*args, **kwargs)

class DeviceCategoryType(enum.IntEnum):
    electric_vehicle = 65536
    virtual_or_mixed_der = 262144
    reciprocating_engine = 524288
    photovoltaic_system = 2097152
    combined_pv_and_storage = 8388608
    other_generation_system = 16777216
    other_storage_system = 33554432

class FunctionsImplementedType(enum.IntEnum):
    device_capability = 0
    selfdevice_resource = 1
    enddevice_resource = 2
    function_set_assignments = 4
    subscription_notification_mechanism = 8
    response = 16
    time = 32
    device_information = 64
    power_status = 128
    network_status = 256
    log_event = 512
    configuration_resource = 1024
    software_download = 2048
    drlc = 4096
    metering = 8192
    pricing = 16384
    messaging = 32768
    billing = 65536
    prepayment = 131072
    flow_reservation = 262144
    der_control = 524288


class GPSLocationType(BaseModel):
    lat: float = Field()
    lon: float = Field()

class PowerSourceType(enum.IntEnum):
    none = 0
    mains = 1
    battery = 2
    local_generation = 3
    emergency = 4
    unknown = 5

class ActivePower(BaseModel):
    multipler: int = 0
    value: float = Field()


class Link(BaseModel):
    href: str = Field(default=None, alias='@href')


class DeviceInformation(BaseModel):
    functions_implemented: Optional[FunctionsImplementedType] = Field(alias='functionsImplemented')
    gps_location: Optional[GPSLocationType] = Field(alias='gpsLocation')
    lfdi:  int = Field(alias='lFDI')
    # mfDate: 
    mf_hw_ver: Optional[str] = Field(alias='mfHwVer')
    mf_id: Optional[int] = Field(alias='mfID')
    mf_info: Optional[str] = Field(alias='mfInfo')
    mf_model: Optional[str] = Field(alias='mfModel')
    mf_ser_num: Optional[str] = Field(alias='mfSerNum')
    primary_power: Optional[PowerSourceType] = Field(alias='primaryPower')
    secondary_power: Optional[PowerSourceType] = Field(alias='secondaryPower')
    sw_act_time: Optional[int] = Field(alias='swActTime')
    sw_ver: Optional[str] = Field(alias='swVer')


class DERCapability(BaseModel):
    modes_supported: int = Field(default=1, alias='modesSupported')
    rtg_max_w: float = Field(alias='rtgMaxW')
    type_: int = Field(alias='type')


class DER(BaseModel):
    der_capability: DERCapability = Field(alias='DERCapability')


class EndDevice(BaseModel):
    device_category: DeviceCategoryType = Field(alias='deviceCategory') # TODO Actually use enum values
    lfdi: str = Field(alias='lFDI')
    sfdi: Optional[str] = Field(alias='sFDI')
    der_list_link: Optional[Link] = Field(default=None, alias="DERListLink")
    device_information_link: Optional[Link] = Field(default=None, alias="DeviceInformationLink")
    der: Optional[List[DER]] = Field(alias='DER')
    device_information: Optional[DeviceInformation] = Field(alias='deviceInformation')

    class Config:
        use_enum_values = True

    class XmlTemplate:
        create = {
            'include': {'device_category', 'lfdi', 'sfdi'},
            'by_alias': True,
        }
        link = {
            'include': {'device_category', 'lfdi', 'sfdi', 'der_list_link', 'DeviceInformationLink'},
            'by_alias': True,
        }
        show = {
            'include': {'device_category', 'lfdi', 'sfdi', 'der', 'device_information'},
            'by_alias': True,
        }


    # @validator('device_category')
    # def to_int(cls, v):
    #     print(v)
    #     return int(v)

    # @validator('lfdi')
    # def convert_to_hex(cls, v):


    @validator('sfdi', always=True)
    def calculate_sfdi(cls, v, values):
        lfdi = int(values.get('lfdi'), 16)
        print(lfdi)
        if lfdi and not v:
            bit_left_truncation_len = 36
            # truncate the lFDI
            sfdi_no_sod_checksum = lfdi>>(lfdi.bit_length()-bit_left_truncation_len)
            # calculate sum-of-digits checksum digit
            sod_checksum = 10 - sum([int(digit) for digit in str(sfdi_no_sod_checksum)])%10
            # right concatenate the checksum digit and return
            return str(sfdi_no_sod_checksum) + str(sod_checksum)
        return v


class EndDeviceList(PydanticList):
    # Can't tell the difference between single item and list in XML, so need to cater to 
    # single item entry
    end_device: Union[List[EndDevice], EndDevice] = Field(alias='EndDevice')
    list_field: Literal["end_device"] = "end_device"

    @validator('end_device')
    def ensure_list(cls, v):
        print(v)
        if not isinstance(v, list):
            return [v]
        return v

    # def dict(self, *args, **kwargs):
    #     return {'EndDeviceList': super().dict(*args, **kwargs)}


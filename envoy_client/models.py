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
    """A sub-class of pydantic `BaseModel` that provides some convenience functions
    around the 

    Args:
        PydanticBaseModel ([type]): [description]

    Returns:
        [type]: [description]
    """
    class Config:
        allow_population_by_field_name = True
        use_enum_values = True

    class XmlTemplate:
        """
        `XmlTemplate` provides per-class configuration options for the generation 
        of XML (or dict) representations from a pydantic `BaseModel`. 
        The three options that should usually be catered for are:
        - create: this is used when generating information for a POST/PUT request
        from the aggregator or device client, to match the required information in the
        utility server API
        - link: this would usually match what a utility server would expect to respond to
        a GET request with. On the client, this is a convenience function for inspection.
        - show: a convenience template for showing the relationships between
        objects (for example an `EndDevice` linked to `DER`, rather than through a `DERListLink`)
        """
        create = {}
        link = {}
        show = {}

    def dict(self, *args, **kwargs) -> dict:
        """Overrides the pydantic `BaseModel.dict` method to use the supplied templates
        when the `mode` is passed in.

        Returns:
            dict: dictionary representation of the object
        """
        if 'mode' in kwargs:
            additional_kwargs = getattr(self.XmlTemplate, kwargs.pop('mode'), {})
            return super().dict(*args, **{**kwargs, **additional_kwargs})
        return super().dict(*args, **kwargs)

    def xml_dict(self, *args, **kwargs) -> dict:
        """Generate a dictionary corresponding to the XML representation of the object,
        when this object is the top level in the XML document.
        This creates an additional (single-entry) dictionary corresponding to the class name
        of the object.
        Note: This should only be called on a top-level document object - children objects
        should not use this method. The `to_xml` function is a better option to generate
        valid XML that conforms to the 2030.5 spec.

        Returns:
            dict: dictionary representation of the object
        """
        return {self.__class__.__name__: self.dict(*args, **kwargs)}

    @classmethod
    def from_xml(cls, document: str) -> 'BaseModel':
        """Parse an XML document to create an instance of this class

        Args:
            document (str): XML document

        Returns:
            BaseModel: Instance of this class.
        """
        return cls(**xmltodict.parse(document)[cls.__name__])

    def to_xml(self, mode='create', pretty=False) -> str:
        """Generate XML according to a particular template from this object 
        (including nested objects)

        Args:
            mode (str, optional): Template to use for creating XML document. Defaults to 'create'.
            pretty (bool, optional): Include whitespace in resulting XML that preserves structure. Defaults to False.

        Returns:
            str: XML document (as string)
        """
        return xmltodict.unparse(self.xml_dict(mode=mode), full_document=False, pretty=pretty)




class PydanticList(BaseModel):
    """Sub-classing of a pydantic `BaseModel` that contains some convenience methods relating
    to the generation of valid XML from a list.

    The `list_field` attribute should correspond to name of the object attribute for which
    a list is to be generated. The generated dictionary is of the following structure:

    ```
    {
        "ObjectList": {
            "Object": [
                {
                    "attribute1": "foo1",
                    "attribute2": "bar1"
                },
                {
                    "attribute1": "foo2",
                    "attribute2": "bar2"
                }
            ]
        }
    }
    ```

    This matches the structure that `xmltodict` uses to generate XML with the following structure:
    ```xml
    <ObjectList>
        <Object>
            <attribute1>foo1</attribute1>
            <attribute2>bar1</attribute2>
        </Object>
        <Object>
            <attribute1>foo2</attribute1>
            <attribute2>bar2</attribute2>
        </Object>
    </ObjectList>
    ```
    """
    list_field: Literal["None"] = "None"

    def dict(self, *args, **kwargs) -> dict:
        """Generate a dictionary corresponding to the structure that would map
        to an XML list.

        Returns:
            dict: Object dictionary representation
        """
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

    def xml_dict(self, *args, **kwargs) -> dict:
        """Generate a dictionary corresponding to the structure of an XML document.
        Identical to `self.dict(*args, **kwargs)`

        Returns:
            dict: object dictionary
        """
        return self.dict(*args, **kwargs)


class DeviceCategoryType(enum.IntEnum):
    """The Device category types defined."""
    electric_vehicle = 65536
    virtual_or_mixed_der = 262144
    reciprocating_engine = 524288
    photovoltaic_system = 2097152
    combined_pv_and_storage = 8388608
    other_generation_system = 16777216
    other_storage_system = 33554432


class FunctionsImplementedType(enum.IntEnum):
    """Bitmap indicating the function sets used by the device as a client.
    """
    # TODO This should be implemented as flags, as they can support compositions of
    # these properties
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
    """Specifies a GPS location, expressed in WGS 84 coordinates."""
    lat: float = Field()
    lon: float = Field()

class PowerSourceType(enum.IntEnum):
    none = 0
    mains = 1
    battery = 2
    local_generation = 3
    emergency = 4
    unknown = 5



class ValueWithMultiplier(BaseModel):
    """Abstract representation of a value with power-of-ten multiplier"""
    multipler: int = 0
    value: int = Field()

    class XmlTemplate:
        create = {
            'include': {'multiplier', 'value'},
            'by_alias': True,
            'exclude_unset': False
        }
        show = create
        list = create

class ActivePower(ValueWithMultiplier):
    """The active (real) power P (in watts) is the product of root mean square (rms) 
    voltage, rms current, and cos(theta) where theta is the phase angle of current 
    relative to voltage. It is the primary measure of the rate of flow of energy.
    """
    pass
    

class ReactivePower(ValueWithMultiplier):
    """The reactive power Q (in var) is the product of root mean square (rms) voltage, 
    rms current, and sin(theta) where theta is the phase angle of current relative to voltage.
    """
    pass


class Link(BaseModel):
    """Generic representation of a link within an XML document"""
    href: str = Field(default=None, alias='@href')


class DeviceInformation(BaseModel):
    """Contains identification and other information about the device that changes very 
    infrequently, typically only when updates are applied, if ever.
    """
    functions_implemented: Optional[FunctionsImplementedType] = Field(alias='functionsImplemented', description='Bitmap indicating the function sets used by the device as a client')
    gps_location: Optional[GPSLocationType] = Field(alias='gpsLocation', description='GPS location of this device')
    lfdi: str = Field(alias='lFDI', description='Long form device identifier')
    mf_date: int = Field(alias='mfDate', default=0, description='Date/time of manufacture') 
    mf_hw_ver: Optional[str] = Field(alias='mfHwVer', default='foo')
    mf_id: Optional[int] = Field(alias='mfID', description='The manufacturer’s IANA Enterprise Number')
    mf_info: Optional[str] = Field(alias='mfInfo', description='Manufacturer dependent information related to the manufacture of this device')
    mf_model: Optional[str] = Field(alias='mfModel', description='Manufacturer’s model number')
    mf_ser_num: Optional[str] = Field(alias='mfSerNum', description='Manufacturer assigned serial number')
    primary_power: Optional[PowerSourceType] = Field(alias='primaryPower', default=PowerSourceType.none, description='Primary source of power')
    secondary_power: Optional[PowerSourceType] = Field(alias='secondaryPower', default=PowerSourceType.none, description='Secondary source of power')
    sw_act_time: Optional[int] = Field(alias='swActTime', default=0, description='Activation date/time of currently running software')
    sw_ver: Optional[str] = Field(alias='swVer', default='NA', description='Currently running software version')

    class XmlTemplate:
        create = {
            'exclude_unset': False,
            'by_alias': True
        }
        show = create
        list = create


class DERType(enum.IntEnum):
    """DER object type

    0 = Not applicable/unknown 1 = Virtual or mixed DER
    2 = Reciprocating engine
    3 = Fuel cell
    4 = Photovoltaic system
    5 = Combined heat and power
    6 = Other generation system
    80 = Other storage system
    81 = Electric vehicle
    82 = EVSE
    83 = Combined PV and storage
    All other values reserved.
    """
    na_unknown = 0
    virtual_or_mixed_DER = 1
    reciprocating_engine = 2
    fuel_cell = 3
    pv_system = 4
    combined_heat_power = 5
    other_generation = 6
    other_storage = 80
    electric_vehicle = 81
    EVSE = 82
    combined_pv_storage = 83


class DERCapability(BaseModel):
    """
    The DER resource exposes the capabilities of a specific distributed energy resource, 
    referred to as its nameplate ratings. Ratings are read-only values established by the 
    DER manufacturer by design or manufactured configuration, for instance, the continuous 
    delivered active power rating capability in watts (rtgMaxW), and are available by reading 
    the DERCapability resource.
    """
    modes_supported: int = Field(default=1, alias='modesSupported')
    rtg_max_a: Optional[ValueWithMultiplier] = Field(alias='rtgMaxA')
    rtg_max_ah: Optional[ValueWithMultiplier] = Field(alias='rtgMaxAh')
    rtg_max_w: Optional[ValueWithMultiplier] = Field(alias='rtgMaxW')
    rtg_max_charge_rate_va: Optional[ValueWithMultiplier] = Field(alias='rtgMaxChargeRateVA')
    rtg_max_charge_rate_w: Optional[ValueWithMultiplier] = Field(alias='rtgMaxChargeRateW')
    rtg_max_discharge_rate_va: Optional[ValueWithMultiplier] = Field(alias='rtgMaxDischargeRateVA')
    rtg_max_discharge_rate_w: Optional[ValueWithMultiplier] = Field(alias='rtgMaxDischargeRateW')
    type_: DERType = Field(alias='type')

    class XmlTemplate:
        create = {
            'by_alias': True,
            'exclude_none': True
        }


class DER(BaseModel):
    """Contains links to DER resources
    """
    der_capability: Optional[DERCapability] = Field(alias='DERCapability')
    class XmlTemplate:
        create = {
            'include': {},
            'by_alias': True,
        }
        link = {}
        show = {}


class ConnectionPoint(BaseModel):
    """Extension object containing information about the connection point to which 
    a device is connected. Under normal circumstances, the `meter_id` attribute
    is used to convey the NMI at the device premise to the utility server.
    
    The `connection_point_id` is normally not used by the aggregator client, as it
    references IDs normally used internally by the DNSP.
    """
    connection_point_id: Optional[str] = Field(alias='connectionPointID')
    meter_id: Optional[str] = Field(alias='meterID')

    class XmlTemplate:
        create = {
            'include': {'connection_point_id', 'meter_id'},
            'by_alias': True
        }
        show = create
        list = create

class EndDevice(BaseModel):
    """Asset container that performs one or more end device functions. Contains information 
    about individual devices in the network.

    In the context of interactions with the utility server, an `EndDevice` is any system
    which interacts directly with the utility server (i.e. an aggregator or DER client)
    or any system for which a client acts on behalf of - for example, a site controller
    that the aggregator is in control of.
    """
    device_category: DeviceCategoryType = Field(alias='deviceCategory') # TODO Actually use enum values
    lfdi: str = Field(alias='lFDI')
    sfdi: Optional[str] = Field(alias='sFDI')
    changed_time: int = Field(default=0, alias='changedTime')
    post_rate: int = Field(default=0, alias='postRate')
    enabled: bool = Field(default=True)
    der_list_link: Optional[Link] = Field(default=None, alias="DERListLink")
    device_information_link: Optional[Link] = Field(default=None, alias="DeviceInformationLink")
    der: Optional[List[DER]] = Field(alias='DER')
    device_information: Optional[DeviceInformation] = Field(alias='deviceInformation')
    connection_point:  Optional[ConnectionPoint] = Field(alias='connectionPoint')

    class XmlTemplate:
        create = {
            'include': {'device_category', 'lfdi', 'sfdi', 'changed_time', 'post_rate', 'enabled'},
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

    @validator('sfdi', always=True)
    def calculate_sfdi(cls, v, values):
        lfdi = int(values.get('lfdi'), 16)
        print(lfdi)
        if lfdi and not v:
            bit_left_truncation_len = 36
            # truncate the lFDI
            sfdi_no_sod_checksum = lfdi>>(lfdi.bit_length()-bit_left_truncation_len)
            # calculate sum-of-digits checksum digit
            sod_checksum = 10 - sum([int(digit) for digit in str(sfdi_no_sod_checksum)]) % 10
            # right concatenate the checksum digit and return
            return str(sfdi_no_sod_checksum) + str(sod_checksum)
        return v


class EndDeviceList(PydanticList):
    """A List element to hold `EndDevice` objects.
    """
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

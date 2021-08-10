


import xmltodict

from envoy_client.models import EndDevice, EndDeviceList

data = """<EndDeviceList all="1" result="1" href="/edev" xmlns="urn:ieee:std:2030.5:ns">
    <EndDevice href="/edev/3">
        <deviceCategory>262144</deviceCategory>
        <lFDI>0x222099d639e</lFDI>
        <sFDI>123412</sFDI>
        <DeviceInformationLink href="/edev/3/di"/>
        <DERListLink href="/edev/3/der" all="0"/>
        <changedTime>0</changedTime>
        <FunctionSetAssignmentsListLink href="/edev/3/fsa" all="0"/>
        <RegistrationLink href="/edev/3/rg"/>
    </EndDevice>
    <EndDevice href="/edev/3">
        <deviceCategory>262144</deviceCategory>
        <lFDI>0x222099d639e</lFDI>
        <sFDI>123412</sFDI>
        <DeviceInformationLink href="/edev/3/di"/>
        <DERListLink href="/edev/3/der" all="0"/>
        <changedTime>0</changedTime>
        <FunctionSetAssignmentsListLink href="/edev/3/fsa" all="0"/>
        <RegistrationLink href="/edev/3/rg"/>
    </EndDevice>
</EndDeviceList>"""


d = xmltodict.parse(data)
x = EndDeviceList(**d['EndDeviceList'])


x.dict(by_alias=True, exclude_unset=True, exclude={'end_device': {'device_category'}})


print(xmltodict.unparse(x.dict(by_alias=True), full_document=False, pretty=True))
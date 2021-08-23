# Envoy client

A DER client for a 2030.5 server. Currently this is only a simple implementation of
device registration as an aggregator. This will later be expanded to cover more complex
examples of both Aggregator Client and DER Client models.

# Usage

This library is a very bare implementation, but can be used in two modes:
- mock requests: in this mode, the client prints out requests that would be made
for a given registration process. This is useful if implementing the client in a different
language
- real requests: use client certificate authentication to interact with a real server.

A simple example making mock requests for an example system can be found in 
`scripts/generate_examples.py`. The usage examples below are based on this script.


## Authorisation

Every request must use TLS client-side certificates to authenticate/authorise with the 
utility server. For interacting with the server, the simplest usage of this library is:

```python
from envoy_client.client import AggregatorClient
from envoy_client.transport import RequestsTransport
from envoy_client.auth import ClientCerticateAuth

cert_path = '/path/to/client.cert'
# The aggregator LFDI (long-form device identifier) is derived
# from the client certificate and will be supplied to the aggregator/client
aggregator_lfdi = '0x21352135135'  

client = AggregatorClient(
    transport=RequestsTransport(
        'https://server-location', 
        auth=ClientCertificateAuth(
            cert=cert_path
        )),
    lfdi=aggregator_lfdi
)
```

## Registration

Under the 2030.5 server model, registration of a device requires a non-neglible number of 
requests. The registration process requires all or most of these:
- create `EndDevice`
- add `DeviceInformation` to the `EndDevice`
- add associated `DER` containers to the `EndDevice`
- populate `DERCapability` for each associated `DER`
- register the `EndDevice` to an associated `ConnectionPoint`

These steps are explained in more detail below.

### POST EndDevice

This registers the `EndDevice` with the server, which corresponds (essentially) to the site
controller. Note that under the aggregator model, the aggregator is also an `EndDevice`.

> Note: The long-form device identifier (LFDI) is a 160-bit unique identifier that is normally 
displayed as a hexadecimal string. For `EndDevice`s that use a TLS certificate to communicate
with the server (e.g. the aggregator itself), this is derived from the certificate fingerprint.
For `EndDevice`s that do not have a certificate issued, (e.g. aggregator-managed controllers),
this should correspond to a globally unique identifier that the aggregator already uses, 
appropriately padded or truncated. (Note that, since the short-form device identifier (SFDI) 
is based on the left-truncated 36 bits of the LFDI, the LFDI should not be left-padded).

> When using the models in this library, the SFDI is automatically calculated from the supplied
LFDI. If implemented separately, use the following information:

> The SFDI SHALL be the certificate fingerprint left-truncated to 36 bits. For display purposes, this SHALL be expressed as 11 decimal (base 10) digits, with an additional sum-of-digits checksum digit right- concatenated. For example:
LFDI left truncated to 36 bits: 0x3E4F45AB3
Expressed as a decimal: 16726121139
Checksum added: 167261211391


#### Example
```
POST https://server-location/edev
Content-Type: application/xml

<?xml version="1.0" encoding="utf-8"?>
<EndDevice>
        <deviceCategory>262144</deviceCategory>
        <lFDI>0x21352135135</lFDI>
        <sFDI>356563223726</sFDI>
        <changedTime>0</changedTime>
        <postRate>0</postRate>
        <enabled>true</enabled>
</EndDevice>

```

The server responds with a `201: CREATED` response and a header `location: /edev/3`
to indicate the location of the created resource. This value is then used in the subsequent 
requests and is referenced in these examples as {edevID}


### PUT DeviceInformation

`DeviceInformation` contains identification and other information about the device that changes very infrequently, typically only when updates are applied, if ever.

#### Example

```
PUT https://server-location/edev/1/di
Content-Type: application/xml

<?xml version="1.0" encoding="utf-8"?>
<DeviceInformation>
        <functionsImplemented>524288</functionsImplemented>
        <gpsLocation>
                <lat>-35.0</lat>
                <lon>144.0</lon>
        </gpsLocation>
        <lFDI>1172794507551</lFDI>
        <mfDate>0</mfDate>
        <mfHwVer>foo</mfHwVer>
        <mfID>1234567</mfID>
        <mfInfo>Acme Corp</mfInfo>
        <mfModel>Acme 2000 Pro+</mfModel>
        <mfSerNum>ACME1234</mfSerNum>
        <primaryPower>0</primaryPower>
        <secondaryPower>0</secondaryPower>
        <swActTime>0</swActTime>
        <swVer>NA</swVer>
</DeviceInformation>
```

### POST DER
An `EndDevice` can have multiple `DER` resources linked to it. For the purposes of this 
example, it is assumed that there is only a single `DER` resource under each `EndDevice`.

```
POST https://server-location/edev/{edevID}/der
Content-Type: application/xml

<?xml version="1.0" encoding="utf-8"?>
<DER></DER>
```

The server responds with a `201: CREATED` response and a header `location: /edev/{edevID}/der/5`
to indicate the location of the resource. For the following examples, this is referenced by
{derID}.


### PUT DER Capability
While a `DER` resource can contain information about `DERSettings`, `DERStatus`, `DERCapability` 
and `DERAvailability`, we are only interested in `DERCapability`, which exposes the nameplate
ratings of the DER.


#### Example



```
PUT https://server-location/edev/{edevID}/der/{derID}/dercap
Content-Type: application/xml

<?xml version="1.0" encoding="utf-8"?>
<DERCapability>
        <modesSupported>1</modesSupported>
        <rtgMaxW>
                <value>5000</value>
                <multiplier>0</multiplier>
        </rtgMaxW>
        <type>83</type>
</DERCapability>
```


### PUT ConnectionPoint

This is an extension to the standard that allows the aggregator or DER client to provide
additional information about the identification of the connection point to which the
device is connected (generally for metering purposes).

#### Example

The client PUTs a `ConnectionPoint` object containing the site NMI (as `meterID`).

```
PUT https://server-location/edev/1/cp
Content-Type: application/xml

<?xml version="1.0" encoding="utf-8"?>
<ConnectionPoint>
        <connectionPointID></connectionPointID>
        <meterID>NMI123</meterID>
</ConnectionPoint>
```

Server responds with `200: OK`.

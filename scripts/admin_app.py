import enum
import logging
import re

import click
import rich.logging
from admin_app_settings import settings
from rich import console as rich_console
from rich.table import Table

from envoy_client import auth, interface, transport
from envoy_client.models import base

logger = logging.getLogger(__name__)
console = rich_console.Console()


@enum.unique
class Format(enum.Enum):
    CSV = "csv"
    TABLE = "table"


def configure_logging():
    logging.basicConfig(
        level=logging.WARNING,
        format="%(message)s",
        datefmt=f"[{logging.Formatter.default_time_format}]",
        handlers=[rich.logging.RichHandler()],
    )

    logger.setLevel(logging.INFO)


def create_client(
    server_url: str,
    certificate_path: str,
    key_path: str,
    aggregator_lfdi: str,
    use_ssl_auth: bool = True,
) -> interface.EndDeviceInterface:
    """Creates a 2030.5 aggregator client with the requested authentication.

    The client is used by aggregators to interface to a 2030.5 server. SSL
    encryption is the default. Disabling SSL encryption (use_ssl_auth=False)
    will only work with a locally deployed servers that have been configured to
    accept unencrypted connections. In this a certificate_path and key_path is
    not required.

    Args:
      server_url: The URL of the 2030.5 server.
      certificate_path: A path to the certificate used for SSL encryption.
      key_path: A path to the key used for SSL encryption.
      aggregator_lfdi: The lFDI of the aggregator as a hex string e.g.
                       "0x1234567890"
      use_ssl_auth: If True uses the certificate given by certificate path to
                    provide SSL encrypted communications to the server.
                    If False no SSL encryption is used.

    Returns:
      The new EndDeviceInterface.
    """
    auth_config = None
    if use_ssl_auth:
        auth_config = auth.ClientCertificateAuth((certificate_path, key_path))
    else:
        auth_config = auth.LocalModeXTokenAuth(aggregator_lfdi)
    transport_config = transport.RequestsTransport(server_url, auth=auth_config)
    return interface.EndDeviceInterface(
        transport=transport_config,
        lfdi=aggregator_lfdi,
    )


def create_default_client():
    return create_client(
        settings.server_url,
        settings.certificate_path,
        settings.key_path,
        settings.client_lfdi,
        use_ssl_auth=settings.use_ssl_auth,
    )


def get_id_from_regex(regex: str, s: str) -> int:
    try:
        id_str = re.fullmatch(regex, s).group(1)
    except AttributeError:
        raise ValueError
    return int(id_str)


def get_edev_id_from_der_link_list_url(url: str) -> int:
    """Parses a der link list url into a edev_id.

    Examples:
        if url is "/edev/42/der" returns 42
        if url is "/edev/1024/der" return 1024

    Args:
        url: a der link list url

    Returns:
        An integer edev_id parsed from the url argument

    Raises:
        ValueError: when the url cannot be parsed into a edev_id
    """
    return get_id_from_regex(r"/edev/(\d+)/der", url)


def get_mup_id_from_url(url: str) -> int:
    return get_id_from_regex(r"/mup/(\d+)", url)


def get_mmr_id_from_url(url: str) -> int:
    return get_id_from_regex(r"/mup/\d+/mmr/(\d+)", url)


def get_reading_id_from_url(url: str) -> int:
    return get_id_from_regex(r"/mmr/\d+/reading/(\d+)", url)


@click.group()
def cli():
    pass


# @cli.command()
# @click.option(
#     "--event", "der_event_id", required=True, type=str, help="Id of the DER Event"
# )
# def event(der_event_id):
#     client = create_default_client()


@cli.command()
def devices():
    client = create_default_client()

    table = Table(
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column(
        "ID",
    )
    table.add_column(
        "lFDI",
    )
    table.add_column("Device Category")
    num_devices = 0
    for paged_result in client.get_paged_end_devices():
        for end_device in paged_result.end_device:
            dc = base.DeviceCategoryType(end_device.device_category)
            edev_id = get_edev_id_from_der_link_list_url(end_device.der_list_link.href)
            table.add_row(
                f"{edev_id}",
                end_device.lfdi,
                dc.name,
            )
            num_devices += 1
    table.caption_justify = "right"
    table.caption_style = "None"
    table.caption = f"Total Devices: [bold magenta]{num_devices}[bold magenta]"
    console.print(table)


@cli.command()
def mups():
    client = create_default_client()

    table = Table(
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column(
        "ID",
    )
    table.add_column(
        "Description",
    )
    table.add_column("Device lFDI")
    num_mups = 0
    for paged_result in client.get_paged_mups():
        # logger.info(paged_result.mirror_usage_point)
        for mup in paged_result.mirror_usage_point:
            mup_id = get_mup_id_from_url(mup.href)
            table.add_row(f"{mup_id}", mup.description, mup.device_lfdi)
            num_mups += 1
    table.caption_justify = "right"
    table.caption_style = "None"
    table.caption = f"Total MUPs: [bold magenta]{num_mups}[bold magenta]"
    console.print(table)


@cli.command()
@click.option(
    "--id", "mup_id", required=True, type=str, help="Id of the Mirror Usage Point"
)
def mup(mup_id):
    client = create_default_client()

    table = Table(
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column(
        "ID",
    )
    table.add_column(
        "Description",
    )
    table.add_column("Device lFDI")
    num_mups = 0
    mups = client.get_mup(mup_id).mirror_usage_point
    for mup in mups:
        mup_id = get_mup_id_from_url(mup.href)
        table.add_row(f"{mup_id}", mup.description, mup.device_lfdi)
        num_mups += 1
    table.caption_justify = "right"
    table.caption_style = "None"
    table.caption = f"Total MUPs: [bold magenta]{num_mups}[bold magenta]"
    console.print(table)


@cli.command()
@click.option(
    "--id", "mup_id", required=True, type=str, help="Id of the Mirror Usage Point"
)
def mmrs(mup_id):
    client = create_default_client()

    table = Table(
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("ID")
    table.add_column(
        "Measure Type (UOM)",
    )
    table.add_column(
        "Phase",
    )
    num_mups = 0
    mmrs = client.get_mmrs(mup_id).mirror_meter_reading
    for mmr in mmrs:
        mmr_id = get_mmr_id_from_url(mmr.href)
        uom = base.UomType(mmr.reading_type.uom)
        table.add_row(f"{mmr_id}", uom.name, f"{mmr.reading_type.phase}")
        num_mups += 1
    table.caption_justify = "right"
    table.caption_style = "None"
    table.caption = f"Total MMRs: [bold magenta]{num_mups}[bold magenta]"
    console.print(table)


@cli.command()
@click.option(
    "--id", "mmr_id", required=True, type=int, help="Id of the Mirror Meter Reading"
)
@click.option(
    "--format",
    type=click.Choice(list(Format.__members__), case_sensitive=False),
    callback=lambda context, parameter, value: getattr(Format, value),
    default=Format.TABLE.value,
)
@click.option(
    "--max", "max_readings", default=50, type=int, help="Max number of readings"
)
def readings(mmr_id: int, format: str, max_readings: int):
    client = create_default_client()
    readings = client.get_readings(mmr_id, limit=max_readings).reading

    if format is Format.TABLE:
        table = Table(
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("ID")
        table.add_column(
            "Start",
        )
        table.add_column(
            "Duration",
        )
        table.add_column("Value")
        num_readings = 0
        for reading in readings:
            reading_id = get_reading_id_from_url(reading.href)
            table.add_row(
                f"{reading_id}",
                f"{reading.time_period.start}",
                f"{reading.time_period.duration}",
                f"{reading.value}",
            )
            num_readings += 1
        table.caption_justify = "right"
        table.caption_style = "None"
        table.caption = f"Total Readings: [bold magenta]{num_readings}[bold magenta]"
        console.print(table)
    if format is Format.CSV:
        print(",".join(["ID", "Start", "Duration", "Value"]))
        for reading in readings:
            reading_id = get_reading_id_from_url(reading.href)
            print(
                ",".join(
                    [
                        f"{reading_id}",
                        f"{reading.time_period.start}",
                        f"{reading.time_period.duration}",
                        f"{reading.value}",
                    ]
                )
            )


@cli.command()
@click.option(
    "--id", "mmr_id", required=True, type=int, help="Id of the Mirror Meter Reading"
)
@click.option(
    "--format",
    type=click.Choice(list(Format.__members__), case_sensitive=False),
    callback=lambda context, parameter, value: getattr(Format, value),
    default=Format.TABLE.value,
)
@click.option(
    "--max", "max_readings", default=50, type=int, help="Max number of readings"
)
def paged_readings(mmr_id: int, format: str, max_readings: int):
    client = create_default_client()
    num_readings = 0
    for paged_result in client.get_paged_readings(mmr_id=mmr_id):
        for reading in paged_result.reading:
            reading_id = get_reading_id_from_url(reading.href)
            print(
                ",".join(
                    [
                        f"{reading_id}",
                        f"{reading.time_period.start}",
                        f"{reading.time_period.duration}",
                        f"{reading.value}",
                    ]
                )
            )
            num_readings += 1
        if num_readings >= max_readings:
            break


if __name__ == "__main__":
    configure_logging()
    cli()

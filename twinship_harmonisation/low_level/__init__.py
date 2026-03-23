"""Low-level functions for creating TwinShip RDF triples.

These are primitive building blocks that wrap RDFLib and create
individual triples or small triple patterns.
"""

from twinship_harmonisation.low_level.boiler_functions import create_twinship_boiler
from twinship_harmonisation.low_level.connection_functions import (
    build_twinship_connection,
    build_twinship_direct_connection,
)
from twinship_harmonisation.low_level.engine_functions import (
    create_twinship_auxiliary_engine,
    create_twinship_main_engine,
)
from twinship_harmonisation.low_level.fuel_functions import (
    build_twinship_fuel_consumption,
    get_twinship_fuel_uri,
)
from twinship_harmonisation.low_level.futuristic_functions import (
    create_twinship_als,
    create_twinship_ammonia_fuel_cell,
    create_twinship_auxiliary_load,
    create_twinship_bow_thruster,
    create_twinship_dc_bus_converter,
    create_twinship_dynamic_wing,
    create_twinship_electric_motor,
    create_twinship_electric_motor_shaft,
    create_twinship_frequency_converter,
    create_twinship_gate_rudder,
    create_twinship_genset,
    create_twinship_scr,
    create_twinship_shore_power,
    create_twinship_wasp,
)
from twinship_harmonisation.low_level.gearbox_functions import create_twinship_gearbox
from twinship_harmonisation.low_level.other_functions import (
    create_twinship_emergency_generator,
    create_twinship_pms,
    create_twinship_shaft_generator,
    create_twinship_thruster,
)
from twinship_harmonisation.low_level.propeller_functions import create_twinship_propeller
from twinship_harmonisation.low_level.vessel_functions import (
    build_pav_provenance,
    create_twinship_uri,
    create_twinship_vessel,
    get_twinship_type_uri,
)

__all__ = [
    "build_pav_provenance",
    "build_twinship_connection",
    "build_twinship_direct_connection",
    "build_twinship_fuel_consumption",
    "create_twinship_als",
    "create_twinship_ammonia_fuel_cell",
    "create_twinship_auxiliary_engine",
    "create_twinship_auxiliary_load",
    "create_twinship_boiler",
    "create_twinship_bow_thruster",
    "create_twinship_dc_bus_converter",
    "create_twinship_dynamic_wing",
    "create_twinship_electric_motor",
    "create_twinship_electric_motor_shaft",
    "create_twinship_emergency_generator",
    "create_twinship_frequency_converter",
    "create_twinship_gate_rudder",
    "create_twinship_gearbox",
    "create_twinship_genset",
    "create_twinship_main_engine",
    "create_twinship_pms",
    "create_twinship_propeller",
    "create_twinship_scr",
    "create_twinship_shaft_generator",
    "create_twinship_shore_power",
    "create_twinship_thruster",
    "create_twinship_uri",
    "create_twinship_vessel",
    "create_twinship_wasp",
    "get_twinship_fuel_uri",
    "get_twinship_type_uri",
]

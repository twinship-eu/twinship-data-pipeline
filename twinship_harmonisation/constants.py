"""Namespace constants for TwinShip ontology and related vocabularies."""

from rdflib import Namespace

# TwinShip ontology namespaces
TWINSHIP = Namespace("https://twin-ship.eu/twinship#")
TWINSHIP_IND = Namespace("https://twin-ship.eu/individuals/")

# IDO - Industrial Data Ontology
IDO = Namespace("http://rds.posccaesar.org/ontology/lis14/rdl/")

# Sensor observation ontologies
SOSA = Namespace("http://www.w3.org/ns/sosa/")
SSN = Namespace("http://www.w3.org/ns/ssn/")

# QUDT - Quantities, Units, Dimensions, Types
QUDT = Namespace("http://qudt.org/schema/qudt/")
QUDT_UNIT = Namespace("http://qudt.org/vocab/unit/")
QUDT_QUANTITY_KIND = Namespace("http://qudt.org/vocab/quantitykind/")

# Standard ontologies
OWL = Namespace("http://www.w3.org/2002/07/owl#")
RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
XSD = Namespace("http://www.w3.org/2001/XMLSchema#")

# Provenance
PAV = Namespace("http://purl.org/pav/")

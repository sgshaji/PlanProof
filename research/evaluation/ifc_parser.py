"""IFC ground truth extraction using IfcOpenShell.

Parses IFC (Industry Foundation Classes) BIM files to extract
ground truth spatial entities and relationships for evaluation.

Mapping:
  IfcSpace       -> Room entity
  IfcWall        -> Boundary entity
  IfcDoor        -> Opening entity
  IfcWindow      -> Opening entity
  IfcRelContainedInSpatialStructure -> CONTAINS relationship
  IfcRelSpaceBoundary -> ADJACENT_TO relationship
"""

import logging
from typing import Optional

from research.evaluation.ground_truth import (
    GroundTruthAnnotation,
    GroundTruthEntity,
    GroundTruthRelationship,
)

logger = logging.getLogger(__name__)


def parse_ifc_file(
    ifc_path: str,
    submission_id: int,
    annotator: str = "ifc_parser",
) -> GroundTruthAnnotation:
    """Parse an IFC file and extract ground truth entities and relationships.

    Args:
        ifc_path: Path to the .ifc file.
        submission_id: The submission this IFC corresponds to.
        annotator: Name of the annotation source.

    Returns:
        GroundTruthAnnotation populated from the IFC model.
    """
    import ifcopenshell

    ifc_model = ifcopenshell.open(ifc_path)
    entities = []
    relationships = []
    entity_counter = 0

    # Map from IFC GlobalId to our entity_id
    ifc_id_map: dict[str, str] = {}

    # Extract IfcSpace -> Room
    for space in ifc_model.by_type("IfcSpace"):
        entity_counter += 1
        eid = f"ifc_room_{entity_counter}"
        ifc_id_map[space.GlobalId] = eid

        props = _extract_space_properties(space)
        match_key = f"{props.get('name', '')}_{props.get('area', '')}"

        entities.append(GroundTruthEntity(
            entity_id=eid,
            entity_type="Room",
            label=space.LongName or space.Name or f"Space {entity_counter}",
            properties=props,
            match_key=match_key,
        ))

    # Extract IfcWall -> Boundary
    for wall in ifc_model.by_type("IfcWall"):
        entity_counter += 1
        eid = f"ifc_boundary_{entity_counter}"
        ifc_id_map[wall.GlobalId] = eid

        entities.append(GroundTruthEntity(
            entity_id=eid,
            entity_type="Boundary",
            label=wall.Name or f"Wall {entity_counter}",
            properties={"name": wall.Name, "global_id": wall.GlobalId},
            match_key=wall.Name or wall.GlobalId,
        ))

    # Extract IfcDoor -> Opening
    for door in ifc_model.by_type("IfcDoor"):
        entity_counter += 1
        eid = f"ifc_opening_{entity_counter}"
        ifc_id_map[door.GlobalId] = eid

        entities.append(GroundTruthEntity(
            entity_id=eid,
            entity_type="Opening",
            label=door.Name or f"Door {entity_counter}",
            properties={
                "name": door.Name,
                "opening_type": "door",
                "global_id": door.GlobalId,
            },
            match_key=door.Name or door.GlobalId,
        ))

    # Extract IfcWindow -> Opening
    for window in ifc_model.by_type("IfcWindow"):
        entity_counter += 1
        eid = f"ifc_opening_{entity_counter}"
        ifc_id_map[window.GlobalId] = eid

        entities.append(GroundTruthEntity(
            entity_id=eid,
            entity_type="Opening",
            label=window.Name or f"Window {entity_counter}",
            properties={
                "name": window.Name,
                "opening_type": "window",
                "global_id": window.GlobalId,
            },
            match_key=window.Name or window.GlobalId,
        ))

    # Extract IfcRelContainedInSpatialStructure -> CONTAINS
    for rel in ifc_model.by_type("IfcRelContainedInSpatialStructure"):
        container_id = ifc_id_map.get(rel.RelatingStructure.GlobalId)
        if container_id is None:
            continue
        for element in rel.RelatedElements:
            element_id = ifc_id_map.get(element.GlobalId)
            if element_id:
                relationships.append(GroundTruthRelationship(
                    source_id=container_id,
                    target_id=element_id,
                    relationship_type="CONTAINS",
                ))

    # Extract IfcRelSpaceBoundary -> ADJACENT_TO
    for rel in ifc_model.by_type("IfcRelSpaceBoundary"):
        space_id = ifc_id_map.get(rel.RelatingSpace.GlobalId) if rel.RelatingSpace else None
        element_id = ifc_id_map.get(
            rel.RelatedBuildingElement.GlobalId
        ) if rel.RelatedBuildingElement else None
        if space_id and element_id:
            relationships.append(GroundTruthRelationship(
                source_id=space_id,
                target_id=element_id,
                relationship_type="ADJACENT_TO",
            ))

    from datetime import date
    annotation = GroundTruthAnnotation(
        submission_id=submission_id,
        annotator=annotator,
        annotation_date=date.today().isoformat(),
        source="ifc",
        entities=entities,
        relationships=relationships,
    )

    logger.info(
        "Parsed IFC: %d entities, %d relationships from %s",
        len(entities), len(relationships), ifc_path,
    )
    return annotation


def _extract_space_properties(space) -> dict:
    """Extract properties from an IfcSpace element."""
    props = {
        "name": space.LongName or space.Name,
        "global_id": space.GlobalId,
    }

    # Try to get area from property sets
    try:
        for definition in space.IsDefinedBy:
            if hasattr(definition, "RelatingPropertyDefinition"):
                pset = definition.RelatingPropertyDefinition
                if hasattr(pset, "HasProperties"):
                    for prop in pset.HasProperties:
                        if hasattr(prop, "Name") and hasattr(prop, "NominalValue"):
                            name_lower = prop.Name.lower()
                            if "area" in name_lower:
                                props["area"] = float(prop.NominalValue.wrappedValue)
                            elif "height" in name_lower:
                                props["height"] = float(prop.NominalValue.wrappedValue)
    except (AttributeError, TypeError, ValueError):
        pass

    return props

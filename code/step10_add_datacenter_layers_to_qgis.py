#!/usr/bin/env python3
"""
step10_add_datacenter_layers_to_qgis.py
=========================================
Adds the new public-data geolocation layers to the layer-ready QGIS project.

Layers added to group "08 — Validation":
  - All DC (master, 1,622 records) with rule-based symbology by hyperscale_flag
  - Hyperscale subset (402 records) — stars only

Symbolisation:
  - hyperscale yes     → large gold star (★ size 8)
  - hyperscale likely  → medium orange star (size 6)
  - hyperscale no      → small grey circle (size 3)
  - hyperscale unknown → tiny open circle (size 2)
  - Planned/announced  → hollow fill on top of above

Run with QGIS Python:
  PROJ_LIB=... GDAL_DATA=... /Applications/QGIS-LTR.app/Contents/MacOS/bin/python3 \
    13_scripts/step10_add_datacenter_layers_to_qgis.py
"""

import os
import sys
import zipfile
import shutil
import re
import uuid

BASE = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
QGZ_IN  = f"{BASE}/12_qgis_projects/working/DataCenter_Suitability_LAYER_READY_INTERPRETATION.qgz"
QGZ_OUT = QGZ_IN  # overwrite in place

OUT_DIR = f"{BASE}/06_VALIDATION/observed_data_center_points"
REL_MASTER = "../../06_VALIDATION/observed_data_center_points/data_centers_7state_public_master_EPSG5070.gpkg"
REL_HS     = "../../06_VALIDATION/observed_data_center_points/hyperscale_data_centers_7state_EPSG5070.gpkg"

# ── Layer IDs ─────────────────────────────────────────────────────────────────
# Generate stable IDs based on deterministic UUIDs
def make_id(base_name: str) -> str:
    """Create a stable QGIS-style layer ID from a name."""
    slug = re.sub(r'[^A-Za-z0-9]', '_', base_name)[:60]
    uid  = str(uuid.uuid5(uuid.NAMESPACE_DNS, base_name)).replace('-', '_')
    return f"{slug}_{uid}"

ID_MASTER = make_id("dc_public_master_1622")
ID_HS     = make_id("dc_hyperscale_402")

# ── EPSG:5070 SRS block (copy from existing project) ─────────────────────────
SRS_5070 = """<srs>
        <spatialrefsys nativeFormat="Wkt">
          <wkt>PROJCRS["NAD83 / Conus Albers",BASEGEOGCRS["NAD83",DATUM["North American Datum 1983",ELLIPSOID["GRS 1980",6378137,298.257222101,LENGTHUNIT["metre",1]]],PRIMEM["Greenwich",0,ANGLEUNIT["degree",0.0174532925199433]],ID["EPSG",4269]],CONVERSION["Conus Albers",METHOD["Albers Equal Area",ID["EPSG",9822]],PARAMETER["Latitude of false origin",23,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8821]],PARAMETER["Longitude of false origin",-96,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8822]],PARAMETER["Latitude of 1st standard parallel",29.5,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8823]],PARAMETER["Latitude of 2nd standard parallel",45.5,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8824]],PARAMETER["Easting at false origin",0,LENGTHUNIT["metre",1],ID["EPSG",8826]],PARAMETER["Northing at false origin",0,LENGTHUNIT["metre",1],ID["EPSG",8827]]],CS[Cartesian,2],AXIS["easting (X)",east,ORDER[1],LENGTHUNIT["metre",1]],AXIS["northing (Y)",north,ORDER[2],LENGTHUNIT["metre",1]],USAGE[SCOPE["Data analysis and small scale data presentation."],AREA["United States (USA) - onshore and offshore."],BBOX[15.56,-180,74.71,180]],ID["EPSG",5070]]</wkt>
          <proj4>+proj=aea +lat_0=23 +lon_0=-96 +lat_1=29.5 +lat_2=45.5 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs</proj4>
          <srsid>2964</srsid>
          <srid>5070</srid>
          <authid>EPSG:5070</authid>
          <description>NAD83 / Conus Albers</description>
          <projectionacronym>aea</projectionacronym>
          <ellipsoidacronym>EPSG:7019</ellipsoidacronym>
          <geographicflag>false</geographicflag>
        </spatialrefsys>
      </srs>"""

# ── Rule-based renderer for master layer ─────────────────────────────────────
def make_symbol_rule(filter_expr, label, shape, color_rgb, size, border_color_rgb=None,
                     border_style="solid", fill_style="solid", opacity=1.0):
    """Generate a rule-based renderer rule XML."""
    r, g, b = color_rgb
    border_r, border_g, border_b = border_color_rgb or (0, 0, 0)
    border_xml = f'<prop v="{border_r},{border_g},{border_b},255" k="color_border_mapunit_scale"/>' if False else ""

    # QGIS simple marker properties
    # shape: star=8, circle=0, square=1, triangle=2, star_filled=8
    shape_to_name = {
        "star": "star",
        "circle": "circle",
        "square": "square",
        "cross": "cross",
    }
    shape_name = shape_to_name.get(shape, "circle")

    fill_color = f"{r},{g},{b},255" if fill_style == "solid" else f"{r},{g},{b},0"
    stroke_color = f"{border_r},{border_g},{border_b},255"

    rule_id = str(uuid.uuid4())

    return f"""<rule filter="{filter_expr}" label="{label}" symbol="0" key="{{{rule_id}}}">
                <symbols>
                  <symbol is_animated="0" alpha="{opacity}" frame_rate="10" clip_to_extent="1" type="marker" name="0" force_rhr="0">
                    <data_defined_properties>
                      <Option type="Map">
                        <Option value="" type="QString" name="name"/>
                        <Option name="properties"/>
                        <Option value="collection" type="QString" name="type"/>
                      </Option>
                    </data_defined_properties>
                    <layer class="SimpleMarker" pass="0" enabled="1" locked="0">
                      <Option type="Map">
                        <Option value="0" type="QString" name="angle"/>
                        <Option value="{fill_color}" type="QString" name="color"/>
                        <Option value="1" type="QString" name="horizontal_anchor_point"/>
                        <Option value="bevel" type="QString" name="joinstyle"/>
                        <Option value="{shape_name}" type="QString" name="name"/>
                        <Option value="0,0" type="QString" name="offset"/>
                        <Option value="3x:0,0,0,0,0,0" type="QString" name="offset_map_unit_scale"/>
                        <Option value="MM" type="QString" name="offset_unit"/>
                        <Option value="{stroke_color}" type="QString" name="outline_color"/>
                        <Option value="{border_style}" type="QString" name="outline_style"/>
                        <Option value="0.4" type="QString" name="outline_width"/>
                        <Option value="3x:0,0,0,0,0,0" type="QString" name="outline_width_map_unit_scale"/>
                        <Option value="MM" type="QString" name="outline_width_unit"/>
                        <Option value="diameter" type="QString" name="scale_method"/>
                        <Option value="{size}" type="QString" name="size"/>
                        <Option value="3x:0,0,0,0,0,0" type="QString" name="size_map_unit_scale"/>
                        <Option value="MM" type="QString" name="size_unit"/>
                        <Option value="1" type="QString" name="vertical_anchor_point"/>
                      </Option>
                      <data_defined_properties>
                        <Option type="Map">
                          <Option value="" type="QString" name="name"/>
                          <Option name="properties"/>
                          <Option value="collection" type="QString" name="type"/>
                        </Option>
                      </data_defined_properties>
                    </layer>
                  </symbol>
                </symbols>
              </rule>"""

def make_rule_based_renderer_master():
    """Full rule-based renderer XML for the master DC layer."""
    # Rules for hyperscale_flag values
    # Gold/yellow star for confirmed hyperscale
    r_yes = make_symbol_rule(
        filter_expr='"hyperscale_flag" = \'yes\'',
        label="Hyperscale — confirmed (cloud operator / hyperscale campus)",
        shape="star",
        color_rgb=(255, 200, 0),
        size=4.5,
        border_color_rgb=(180, 120, 0),
    )
    # Orange star for likely hyperscale
    r_likely = make_symbol_rule(
        filter_expr='"hyperscale_flag" = \'likely\'',
        label="Hyperscale — likely (large campus / hyperscale-adjacent)",
        shape="star",
        color_rgb=(255, 140, 0),
        size=3.5,
        border_color_rgb=(160, 80, 0),
    )
    # Medium grey circle for colocation/non-hyperscale
    r_no = make_symbol_rule(
        filter_expr='"hyperscale_flag" = \'no\'',
        label="Colocation / enterprise / edge (not hyperscale)",
        shape="circle",
        color_rgb=(150, 150, 150),
        size=2.0,
        border_color_rgb=(100, 100, 100),
    )
    # Small open circle for unknown classification
    r_unk = make_symbol_rule(
        filter_expr='"hyperscale_flag" = \'unknown\' OR "hyperscale_flag" IS NULL',
        label="Classification unknown (commercial directory, unverified)",
        shape="circle",
        color_rgb=(200, 200, 200),
        size=1.5,
        border_color_rgb=(120, 120, 120),
        fill_style="hollow",
    )

    return f"""<renderer-v2 type="RuleRenderer" symbollevels="0" referencescale="-1" enableorderby="0" forceraster="0">
      <rules key="{{{str(uuid.uuid4())}}}">
        {r_yes}
        {r_likely}
        {r_no}
        {r_unk}
      </rules>
      <effect enabled="0" type="effectStack">
        <effect type="dropShadow"/>
        <effect type="outerGlow"/>
        <effect type="drawSource"/>
        <effect type="innerGlow"/>
        <effect type="innerShadow"/>
      </effect>
    </renderer-v2>"""

def make_rule_based_renderer_hyperscale():
    """Rule-based renderer for hyperscale-only layer — stars with size by flag."""
    r_yes = make_symbol_rule(
        filter_expr='"hyperscale_flag" = \'yes\'',
        label="Hyperscale confirmed (AWS / Azure / Google / Meta / Apple / Oracle)",
        shape="star",
        color_rgb=(255, 215, 0),     # gold
        size=5.5,
        border_color_rgb=(160, 100, 0),
    )
    r_likely = make_symbol_rule(
        filter_expr='"hyperscale_flag" = \'likely\'',
        label="Hyperscale likely (large campus, hyperscale-adjacent)",
        shape="star",
        color_rgb=(255, 140, 0),     # orange
        size=4.0,
        border_color_rgb=(140, 70, 0),
    )
    return f"""<renderer-v2 type="RuleRenderer" symbollevels="0" referencescale="-1" enableorderby="0" forceraster="0">
      <rules key="{{{str(uuid.uuid4())}}}">
        {r_yes}
        {r_likely}
      </rules>
      <effect enabled="0" type="effectStack">
        <effect type="dropShadow"/>
        <effect type="outerGlow"/>
        <effect type="drawSource"/>
        <effect type="innerGlow"/>
        <effect type="innerShadow"/>
      </effect>
    </renderer-v2>"""

# ── Maplayer XML block ────────────────────────────────────────────────────────
def make_maplayer_xml(layer_id, name, datasource, renderer_xml, n_features, is_visible=True):
    """Generate a <maplayer> XML block for a vector point layer."""
    return f"""<maplayer symbologyReferenceScale="-1" hasScaleBasedVisibilityFlag="0" simplifyMaxScale="1" autoRefreshMode="Disabled" simplifyDrawingTol="1" geometry="Point" refreshOnNotifyEnabled="0" wkbType="Point" readOnly="0" maxScale="0" styleCategories="AllStyleCategories" autoRefreshTime="0" legendPlaceholderImage="" simplifyAlgorithm="0" minScale="100000000" simplifyDrawingHints="1" simplifyLocal="1" labelsEnabled="0" refreshOnNotifyMessage="" type="vector">
      <id>{layer_id}</id>
      <datasource>{datasource}</datasource>
      <keywordList>
        <value>validation</value>
        <value>data centres</value>
        <value>public data</value>
        <value>not a scoring input</value>
      </keywordList>
      <layername>{name}</layername>
      {SRS_5070}
      <provider encoding="UTF-8">ogr</provider>
      <vectorjoins/>
      <layerGeometryType>0</layerGeometryType>
      {renderer_xml}
      <blendMode>0</blendMode>
      <featureBlendMode>0</featureBlendMode>
      <layerOpacity>1</layerOpacity>
      <SingleCategoryDiagramRenderer diagramType="Histogram" attributeLegend="1">
        <DiagramCategory minScaleDenominator="0" maxScaleDenominator="1e+08" enabled="0"/>
      </SingleCategoryDiagramRenderer>
      <DiagramLayerSettings linePlacementFlags="18" showAll="1" priority="0" obstacle="0" dist="0" placement="0" zIndex="0">
        <properties/>
      </DiagramLayerSettings>
      <geometryOptions removeDuplicateNodes="0" geometryPrecision="0">
        <activeChecks/>
        <checkConfiguration/>
      </geometryOptions>
      <legend showLabelLegend="0" type="default-vector"/>
      <mapTip enabled="1"/>
    </maplayer>"""

# ── Layer tree entries ────────────────────────────────────────────────────────
def make_layer_tree_entry(layer_id, name, source, checked=True):
    check = "Qt::Checked" if checked else "Qt::Unchecked"
    return f"""<layer-tree-layer legend_exp="" patch_size="-1,-1" source="{source}" providerKey="ogr" checked="{check}" id="{layer_id}" legend_split_behavior="0" name="{name}" expanded="1">
        <customproperties>
          <Option/>
        </customproperties>
      </layer-tree-layer>"""

# ── Subgroup XML ─────────────────────────────────────────────────────────────
def make_subgroup(name, entries_xml, checked=True):
    check = "Qt::Checked" if checked else "Qt::Unchecked"
    return f"""<layer-tree-group groupLayer="" checked="{check}" name="{name}" expanded="1">
      <customproperties>
        <Option/>
      </customproperties>
      {entries_xml}
    </layer-tree-group>"""

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"Loading QGZ: {QGZ_IN}")

    # Read existing QGZ
    tmp_qgz = QGZ_IN + ".tmp_step10"
    shutil.copy2(QGZ_IN, tmp_qgz)

    with zipfile.ZipFile(QGZ_IN) as z:
        qgs_names = [n for n in z.namelist() if n.endswith('.qgs')]
        if not qgs_names:
            raise RuntimeError("No .qgs file found in QGZ")
        qgs_name = qgs_names[0]
        content = z.read(qgs_name).decode('utf-8', errors='replace')
        other_files = {n: z.read(n) for n in z.namelist() if n != qgs_name}

    print(f"  QGS file: {qgs_name}")
    print(f"  Initial layer count: {len(re.findall('<maplayer ', content))}")

    # Check if layers already exist (avoid duplicating on re-run)
    if ID_MASTER in content:
        print("  Master layer already in project — skipping re-add")
    else:
        # ── 1. Build new maplayer XML blocks ─────────────────────────────────
        master_renderer = make_rule_based_renderer_master()
        master_layer_xml = make_maplayer_xml(
            layer_id=ID_MASTER,
            name="All Data Centres — Public-Data Geolocation (1,622 pts | VALIDATION ONLY — not a scoring input)",
            datasource=REL_MASTER,
            renderer_xml=master_renderer,
            n_features=1622,
            is_visible=True,
        )

        hs_renderer = make_rule_based_renderer_hyperscale()
        hs_layer_xml = make_maplayer_xml(
            layer_id=ID_HS,
            name="Hyperscale & Major Data Centres (402 pts | VALIDATION ONLY — public-data geolocation)",
            datasource=REL_HS,
            renderer_xml=hs_renderer,
            n_features=402,
            is_visible=True,
        )

        # ── 2. Insert maplayer blocks before </projectlayers> ─────────────────
        insert_pos = content.rfind("</projectlayers>")
        if insert_pos < 0:
            raise RuntimeError("Cannot find </projectlayers> in QGS XML")

        new_layers_xml = f"\n    {master_layer_xml}\n    {hs_layer_xml}\n"
        content = content[:insert_pos] + new_layers_xml + content[insert_pos:]
        print("  Inserted 2 new maplayer definitions")

        # ── 3. Add layer tree entries to validation group ─────────────────────
        # Find validation group
        val_group_tag = '<layer-tree-group groupLayer="" checked="Qt::Checked" name="08 — Validation'
        val_start = content.find(val_group_tag)
        if val_start < 0:
            raise RuntimeError("Cannot find validation group in layer tree")

        # Find the first <layer-tree-layer> inside this group to insert before it
        insert_after = content.find('</customproperties>', val_start)
        insert_after = content.find('\n', insert_after) + 1

        # Build subgroup with both new layers
        entry_master = make_layer_tree_entry(
            ID_MASTER,
            "All Data Centres — Public-Data Geolocation (1,622 pts | VALIDATION ONLY — not a scoring input)",
            REL_MASTER,
            checked=True,
        )
        entry_hs = make_layer_tree_entry(
            ID_HS,
            "Hyperscale & Major Data Centres (402 pts | VALIDATION ONLY — public-data geolocation)",
            REL_HS,
            checked=True,
        )

        subgroup_xml = make_subgroup(
            "08a — Observed Data Centres (public-data geolocation 2026-06-22 | VALIDATION ONLY)",
            entry_master + "\n      " + entry_hs,
            checked=True,
        )

        subgroup_xml_indented = "\n      " + subgroup_xml.replace("\n", "\n      ") + "\n"
        content = content[:insert_after] + subgroup_xml_indented + content[insert_after:]
        print("  Inserted layer tree subgroup '08a — Observed Data Centres'")

    # ── 4. Write updated QGZ ──────────────────────────────────────────────────
    qgz_final = QGZ_IN + ".step10_new"
    with zipfile.ZipFile(qgz_final, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
        zout.writestr(qgs_name, content.encode('utf-8'))
        for fname, fdata in other_files.items():
            zout.writestr(fname, fdata)

    # Replace original
    shutil.move(qgz_final, QGZ_OUT)
    os.remove(tmp_qgz)

    print(f"\n  Final layer count: {len(re.findall('<maplayer ', content))}")
    print(f"  QGZ saved: {QGZ_OUT}")
    print("  Done.")

if __name__ == "__main__":
    main()

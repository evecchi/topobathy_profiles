# -*- coding: utf-8 -*-

from qgis.core import (
    QgsGeometry,
    QgsFeatureRequest
)


def extract_points_along_section(
    section_layer,
    point_layers,
    elevation_fields,
    use_z_geometry_flags,
    buffer_distance,
    min_plot_spacing,
    section_id_field,
    selected_feature_ids=None,
    progress_callback=None,
    split_profile_on_max_distance=False,     # <-- AGGIUNTO
    max_segment_length=0.0                   # <-- AGGIUNTO
):
    """
    Extract profile data from multiple point layers along selected section(s).

    Supports:
    - Multiple point layers
    - Elevation field per layer
    - Optional Z geometry per layer
    - Buffer filtering
    - Minimum spacing thinning
    - Multi-section support
    - Optional split of profile line if consecutive points are too far
    """

    results = []

    if selected_feature_ids:
        request = QgsFeatureRequest().setFilterFids(selected_feature_ids)
        section_features = section_layer.getFeatures(request)
    else:
        section_features = section_layer.getFeatures()

    for section_feat in section_features:

        section_id = section_feat[section_id_field]
        geom = section_feat.geometry()

        if geom.isMultipart():
            geom = QgsGeometry.fromPolylineXY(geom.asMultiPolyline()[0])

        section_data = {}

        # Loop over each point layer
        for i, layer in enumerate(point_layers):

            elev_field = elevation_fields[i]
            use_z = use_z_geometry_flags[i]

            x_vals = []
            y_vals = []

            buffer_geom = geom.buffer(buffer_distance, 8)

            request_points = QgsFeatureRequest().setFilterRect(
                buffer_geom.boundingBox()
            )

            for pt_feat in layer.getFeatures(request_points):

                pt_geom = pt_feat.geometry()

                if not pt_geom.intersects(buffer_geom):
                    continue

                # Distance along line
                distance_along = geom.lineLocatePoint(pt_geom)

                if distance_along < 0:
                    continue

                # Elevation extraction
                if use_z:
                    try:
                        geom_point = pt_geom.constGet()
                        elevation = float(geom_point.z())
                    except Exception:
                        continue
                else:
                    try:
                        elevation = float(pt_feat[elev_field])
                    except (TypeError, ValueError):
                        continue

                x_vals.append(distance_along)
                y_vals.append(elevation)

            # No data case
            if not x_vals:
                section_data[layer.name()] = {
                    "x_plot": [],
                    "y_plot": []
                }
                if progress_callback:
                    progress_callback()
                continue

            # Sort by distance
            sorted_pairs = sorted(zip(x_vals, y_vals), key=lambda x: x[0])
            x_sorted = [p[0] for p in sorted_pairs]
            y_sorted = [p[1] for p in sorted_pairs]

            # Apply minimum spacing filter
            if min_plot_spacing > 0:
                x_filtered = [x_sorted[0]]
                y_filtered = [y_sorted[0]]

                for x, y in zip(x_sorted[1:], y_sorted[1:]):
                    if abs(x - x_filtered[-1]) >= min_plot_spacing:
                        x_filtered.append(x)
                        y_filtered.append(y)

                x_sorted = x_filtered
                y_sorted = y_filtered

            # ----------------------------------------
            # SPLIT PROFILE LINE IF DISTANCE TOO LARGE
            # ----------------------------------------
            if split_profile_on_max_distance and max_segment_length > 0 and len(x_sorted) > 1:
                x_split = [x_sorted[0]]
                y_split = [y_sorted[0]]

                for x, y in zip(x_sorted[1:], y_sorted[1:]):
                    if abs(x - x_split[-1]) > max_segment_length:
                        # insert break in profile
                        x_split.append(None)
                        y_split.append(None)

                    x_split.append(x)
                    y_split.append(y)

                x_sorted = x_split
                y_sorted = y_split

            section_data[layer.name()] = {
                "x_plot": x_sorted,
                "y_plot": y_sorted
            }

            if progress_callback:
                progress_callback()

        results.append({
            "id": section_id,
            "data": section_data
        })

    return results

# -*- coding: utf-8 -*-
import math

def estrai_punti_per_sezione_plugin(
    section_layer,
    punti_layers,
    buffer_dist=4.0,
    passo=0.5,
    distanza_max_plot=30,
    filtra_punti=False,
    distanza_min_plot=5.0,
    feature_id=None
):
    risultati = []

    features = [f for f in section_layer.getFeatures() if feature_id is None or f.id() == feature_id]
    for feat_sez in features:
        linea = feat_sez.geometry()
        lunghezza = linea.length()
        D_values = [i*passo for i in range(int(lunghezza/passo)+1)]
        dati_sezione={}

        bbox = linea.boundingBox()
        bbox.grow(buffer_dist)

        for lyr in punti_layers:
            punti_dati=[]
            for f in lyr.getFeatures():
                if not bbox.contains(f.geometry().boundingBox()):
                    continue
                geom = f.geometry()
                if linea.distance(geom) > buffer_dist:
                    continue
                D_line = linea.lineLocatePoint(geom)
                h_fields = [fld for fld in f.fields().names() if "H" in fld]
                H_val = f[h_fields[0]] if h_fields else None
                punti_dati.append({"geom":geom,"D_line":D_line,"H":H_val})

            punti_selezionati=[]
            for D in D_values:
                subset=[p for p in punti_dati if D<=p["D_line"]<D+passo]
                if subset:
                    punti_selezionati.append(min(subset,key=lambda x:linea.distance(x["geom"])))

            # FILTRO PUNTI VICINI
            if filtra_punti and distanza_min_plot>0:
                filtrati=[]
                last_D=None
                for p in punti_selezionati:
                    if last_D is None or (p["D_line"]-last_D)>=distanza_min_plot:
                        filtrati.append(p)
                        last_D=p["D_line"]
                punti_selezionati=filtrati

            x_plot=[]
            y_plot=[]
            if punti_selezionati:
                try:
                    x0,y0=list(linea.asPolyline())[0].x(), list(linea.asPolyline())[0].y()
                except Exception:
                    x0,y0=list(linea.constGet()[0])[0].x(),list(linea.constGet()[0])[0].y()

                for i,p in enumerate(punti_selezionati):
                    pt=p["geom"].asPoint()
                    D=math.hypot(pt.x()-x0, pt.y()-y0)
                    if i>0 and D-x_plot[-1]>distanza_max_plot:
                        x_plot.append(None)
                        y_plot.append(None)
                    x_plot.append(D)
                    y_plot.append(p["H"])

            dati_sezione[lyr.name()] = {"punti":punti_selezionati,"x_plot":x_plot,"y_plot":y_plot}
        risultati.append(dati_sezione)

    return risultati

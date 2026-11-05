"""Geometría 3D proyectada por software para el motor y el péndulo.

Ejes: x a la derecha, y arriba, z hacia el observador; el eje del motor es z.
Las dimensiones son ilustrativas y no alteran el modelo físico.
"""
import math
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF, QRadialGradient, QLinearGradient, QFont
from .theme import BG, PLOT, LINE, MUTED, LIME, CORAL, CYAN, METAL, METAL_DARK, FONT_BODY


def render_pendulum(widget, painter, radius):
    p = painter
    w, h = widget.width(), widget.height()
    cx, cy = w*.5, h*.48
    scale = radius / 2.65
    background = QRadialGradient(QPointF(w*.5, h*.43), max(w,h)*.73)
    for at, color in ((0,LINE),(.6,PLOT),(1,BG)):
        background.setColorAt(at, QColor(color))
    p.fillRect(widget.rect(), background)

    # Guía angular permanece detrás del mecanismo para no tapar el motor.
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor(LINE), .8))
    p.drawEllipse(QPointF(cx,cy), radius, radius)
    for deg in range(0,360,15):
        a=math.radians(deg)
        p.setPen(QPen(QColor('#678a99' if deg%45==0 else '#3b5d70'), 1))
        p.drawLine(QPointF(cx+radius*math.sin(a),cy-radius*math.cos(a)),
                   QPointF(cx+(radius-(7 if deg%45==0 else 3))*math.sin(a),cy-(radius-(7 if deg%45==0 else 3))*math.cos(a)))
    ref=widget.reference_angle
    p.setPen(QPen(QColor(LIME), 1.2, Qt.PenStyle.DashLine))
    p.drawLine(QPointF(cx,cy), QPointF(cx+radius*math.sin(ref),cy-radius*math.cos(ref)))
    p.setFont(QFont(FONT_BODY,9,QFont.Weight.DemiBold))
    p.setPen(QColor(LIME))
    p.drawText(QRectF(cx+radius*math.sin(ref)-35,cy-radius*math.cos(ref)-19,70,18),Qt.AlignmentFlag.AlignCenter,f'{math.degrees(ref):g}°')

    def project(v):
        x,y,z=v
        # El centro de la guía coincide con el eje al que se une la varilla.
        return QPointF(cx+scale*(x+.12*(z-.98)),cy-scale*(y+.04*(z-.98)))

    faces=[]
    layer = 0
    def face(vertices, color):
        # Aumentar únicamente soporte y carcasa: la varilla conserva su longitud
        # respecto a la escala angular y sigue siendo la figura dominante.
        if layer <= 1:
            vertices = tuple((x*1.12, y*1.12, z) for x, y, z in vertices)
        # Orden ortográfico por profundidad aparente; iluminación por normales.
        a,b,c=vertices[:3]
        ux,uy,uz=(b[i]-a[i] for i in range(3))
        vx,vy,vz=(c[i]-a[i] for i in range(3))
        nx,ny,nz=uy*vz-uz*vy,uz*vx-ux*vz,ux*vy-uy*vx
        length=math.sqrt(nx*nx+ny*ny+nz*nz) or 1
        light=abs((nx*(-.3)+ny*.6+nz*.74)/length)
        base=QColor(color)
        factor=.58+.42*light
        shade=QColor(int(base.red()*factor),int(base.green()*factor),int(base.blue()*factor))
        depth=sum(v[2]-.12*v[0]-.04*v[1] for v in vertices)/len(vertices)
        faces.append((layer, depth, vertices, shade))

    def box(x1,y1,z1,x2,y2,z2,color):
        a=(x1,y1,z1);b=(x2,y1,z1);c=(x2,y2,z1);d=(x1,y2,z1)
        e=(x1,y1,z2);f=(x2,y1,z2);g=(x2,y2,z2);h=(x1,y2,z2)
        for panel in ((a,b,c,d),(e,f,g,h),(a,e,h,d),(b,f,g,c),(d,c,g,h),(a,b,f,e)):
            face(panel,color)

    def cylinder(x,y,z1,z2,r,color,n=24):
        back=[(x+r*math.cos(i*2*math.pi/n),y+r*math.sin(i*2*math.pi/n),z1) for i in range(n)]
        front=[(v[0],v[1],z2) for v in back]
        face(back,color);face(front,color)
        for i in range(n): face((back[i],back[(i+1)%n],front[(i+1)%n],front[i]),color)

    # La base y el soporte sujetan la carcasa estacionaria del motor.
    box(-1.75,-1.15,-1.15,1.75,-.96,.60,'#587582')
    box(-1.20,-.96,-.85,-1.02,-.52,.30,'#7796a1')
    box(1.02,-.96,-.85,1.20,-.52,.30,'#7796a1')
    box(-1.20,-.64,-.85,1.20,-.49,.30,'#627f8e')
    # Carcasa cilíndrica del motor, tapa trasera, brida y eje.
    layer = 1
    cylinder(0,0,-1.18,.28,.70,'#789eae')
    cylinder(0,0,-1.27,-1.18,.57,METAL_DARK)
    cylinder(0,0,.28,.42,.73,'#c1d4d7')
    cylinder(0,0,.42,.51,.48,'#476878')
    cylinder(0,0,.51,.88,.20,'#d2e3e2')
    # Nervaduras en el cuerpo del motor, paralelas al eje.
    for deg in range(0,360,30):
        a=math.radians(deg); x=.704*math.cos(a); y=.704*math.sin(a)
        cylinder(x,y,-1.05,.18,.025,'#9ab0b5',8)
    layer = 2
    # Varilla prismática unida rígidamente al eje; gira en el plano x-y.
    a=widget.angle
    def rot(x,y,z):
        return (x*math.cos(a)+y*math.sin(a), -x*math.sin(a)+y*math.cos(a),z)
    def rod(y1,y2,half,z1,z2,color):
        vertices=[rot(x,y,z) for x,y,z in ((-half,y1,z1),(half,y1,z1),(half,y2,z1),(-half,y2,z1),(-half,y1,z2),(half,y1,z2),(half,y2,z2),(-half,y2,z2))]
        for ids in ((0,1,2,3),(4,5,6,7),(0,4,7,3),(1,5,6,2),(3,2,6,7),(0,1,5,4)):
            face(tuple(vertices[i] for i in ids),color)
    rod(.08,2.45,.095,.84,1.04,'#9cb8c1')
    rod(2.13,2.50,.22,.78,1.12,LIME)
    # La abrazadera gira con la varilla, sobre la punta del eje.
    layer = 3
    cylinder(0,0,.85,1.12,.31,'#355b6b')
    cylinder(0,0,1.12,1.17,.19,CYAN)
    bezel_drawn = False
    for current_layer, depth, vertices, shade in sorted(faces,key=lambda item:(item[0],item[1])):
        if current_layer >= 2 and not bezel_drawn:
            # Bisel y reflejo de la tapa frontal, dibujados detrás de la varilla.
            center = project((0, 0, .43))
            flange_radius = scale*.73*1.12
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(218, 240, 238, 175), max(.8, scale*.025)))
            p.drawEllipse(center, flange_radius*.97, flange_radius*.97)
            reflection = QLinearGradient(center.x(), center.y()-flange_radius,
                                         center.x(), center.y()+flange_radius)
            reflection.setColorAt(0, QColor(226, 245, 240, 95))
            reflection.setColorAt(.45, QColor(148, 195, 202, 20))
            reflection.setColorAt(1, QColor(15, 39, 54, 75))
            p.setPen(QPen(QColor(24, 48, 61, 130), max(.6, scale*.014)))
            p.setBrush(reflection)
            p.drawEllipse(center, flange_radius*.63, flange_radius*.63)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(215, 240, 238, 125), max(.6, scale*.018)))
            p.drawArc(QRectF(center.x()-flange_radius*.57, center.y()-flange_radius*.57,
                             flange_radius*1.14, flange_radius*1.14), 35*16, 115*16)
            bezel_drawn = True
        p.setBrush(shade)
        p.setPen(QPen(shade.darker(145),.6))
        p.drawPolygon(QPolygonF([project(v) for v in vertices]))

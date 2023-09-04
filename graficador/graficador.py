import glfw
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import ctypes
from PIL import Image

texture_path = "texturas/pared.jpg"  # Provide the path to your texture image
texture_id = None

gCamAng = 0.
gCamHeight = 3.
gCursorXPos = 0.0
gCursorYPos = 0.0
is_mouse_dragging = False
prev_cursor_x = 0.0
prev_cursor_y = 0.0
scroll_sensitivity = 1.0

vertices = None 
normals = None
faces = None
dropped = 0
modeFlag = 0
distanceFromOrigin = 45


def load_texture(path):
    global texture_id
    image = Image.open(path)
    img_data = np.array(list(image.getdata()), np.uint8)
    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, image.width, image.height, 0, GL_RGB, GL_UNSIGNED_BYTE, img_data)
    glBindTexture(GL_TEXTURE_2D, 0)

def scroll_callback(window, xoffset, yoffset):
    global gCamHeight, scroll_sensitivity
    gCamHeight -= yoffset * scroll_sensitivity

def cursor_pos_callback(window, xpos, ypos):
    global gCursorXPos, gCursorYPos, gCamAng, gCamHeight, is_mouse_dragging, prev_cursor_x, prev_cursor_y
    
    if is_mouse_dragging:

        dx = xpos - prev_cursor_x
        dy = ypos - prev_cursor_y
        sensitivity = 0.05
        gCamAng -= dx * sensitivity
        gCamHeight += dy * sensitivity

    prev_cursor_x = xpos
    prev_cursor_y = ypos

def mouse_button_callback(window, button, action, mods):
    global is_mouse_dragging

    if button == glfw.MOUSE_BUTTON_LEFT:
        if action == glfw.PRESS:
            is_mouse_dragging = True
        elif action == glfw.RELEASE:
            is_mouse_dragging = False

def dropCallback(window, paths):
    global vertices, normals, faces, dropped, gVertexArraySeparate
    numberOfFacesWith3Vertices = 0
    numberOfFacesWith4Vertices = 0
    numberOfFacesWithMoreThan4Vertices = 0
    dropped = 1
    fileName = paths[0].split('\\')[-1]
    if(paths[0].split('.')[1].lower() != "obj"):
        print("Invalid File\nPlease provide an .obj file")
        return
    with open(paths[0]) as f:
        lines = f.readlines()
        vStrings = [x.strip('v') for x in lines if x.startswith('v ')]
        vertices = convertVertices(vStrings)
        if np.amax(vertices) <= 1.2:
            vertices /= np.amax(vertices)
        else:
            vertices /= np.amax(vertices)/2
        vnStrings = [x.strip('vn') for x in lines if x.startswith('vn')]
        if not vnStrings: #if There is no normal vectors in the obj file then compute them
            normals = fillNormalsArray(len(vStrings))
        else:
            normals = convertVertices(vnStrings)
        faces = [x.strip('f') for x in lines if x.startswith('f')]
    for face in faces: 
        if len(face.split()) == 3:
            numberOfFacesWith3Vertices +=1
        elif len(face.split()) == 4:
            numberOfFacesWith4Vertices +=1
        else:
            numberOfFacesWithMoreThan4Vertices +=1
    print("File name:",fileName,"\nTotal number of faces:", len(faces),
        "\nNumber of faces with 3 vertices:",numberOfFacesWith3Vertices, 
        "\nNumber of faces with 4 vertices:",numberOfFacesWith4Vertices,
        "\nNumber of faces with more than 4 vertices:",numberOfFacesWithMoreThan4Vertices)
    if(numberOfFacesWith4Vertices > 0 or numberOfFacesWithMoreThan4Vertices > 0):
        faces = triangulate()
    gVertexArraySeparate = createVertexArraySeparate()

    ##########EMPTYING USELESS VARIABLES FOR MEMORY MANAGEMENT##########
    faces = []
    normals = []
    vertices = []
    ####################################################################

def fillNormalsArray(numberOfVertices):
    normals = np.zeros((numberOfVertices, 3))
    i = 0
    for vertice in vertices:
        normals[i] = normalized(vertice)
        i +=1
    return normals

def convertVertices(verticesStrings):
    v = np.zeros((len(verticesStrings), 3))
    i = 0
    for vertice in verticesStrings:
        j = 0
        for t in vertice.split():
            try:
                v[i][j] = (float(t))
            except ValueError:
                pass
            j+=1
        i+=1
    return v

def triangulate():
    facesList = []
    nPolygons = []
    for face in faces:
        if(len(face.split())>=4):
            nPolygons.append(face)
        else:
            facesList.append(face)
    for face in nPolygons:
        for i in range(1, len(face.split())-1):
            seq = [str(face.split()[0]), str(face.split()[i]), str(face.split()[i+1])]
            string = ' '.join(seq)
            facesList.append(string)
    return facesList

def createVertexArraySeparate():
    varr = np.zeros((len(faces)*6,3), 'float32')
    i=0
    normalsIndex = 0
    verticeIndex = 0
    for face in faces:
        for f in face.split():
            if '//' in f: # f v//vn
                verticeIndex = int(f.split('//')[0])-1 
                normalsIndex = int(f.split('//')[1])-1
            elif '/' in f: 
                if len(f.split('/')) == 2: # f v/vt
                    verticeIndex = int(f.split('/')[0])-1 
                    normalsIndex = int(f.split('/')[0])-1
                else: # f v/vt/vn
                    verticeIndex = int(f.split('/')[0])-1 
                    normalsIndex = int(f.split('/')[2])-1
            else: # f v v v
                verticeIndex = int(f.split()[0])-1 
                normalsIndex = int(f.split()[0])-1
            varr[i] = normals[normalsIndex]
            varr[i+1] = vertices[verticeIndex]
            i+=2
    return varr

def render(ang):
    global gCamAng, gCamHeight, distanceFromOrigin, dropped, texture_id
    glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)

    glEnable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION) # use projection matrix stack for projection transformation for correct lighting
    glLoadIdentity()
    gluPerspective(distanceFromOrigin, 1, 1,10)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    gluLookAt(5*np.sin(gCamAng),gCamHeight,5*np.cos(gCamAng), 0,0,0, 0,1,0)

    glEnable(GL_TEXTURE_2D)  # Enable 2D texturing
    glBindTexture(GL_TEXTURE_2D, texture_id)
    
    drawFrame()
    glEnable(GL_LIGHTING)   #comment: no lighting
    glEnable(GL_LIGHT0)
    glEnable(GL_LIGHT1)
    glEnable(GL_LIGHT2)

    # light position
    glPushMatrix()
    lightPos0 = (1.,2.,3.,-1.)    # try to change 4th element to 0. or 1.
    lightPos1 = (3.,2.,1.,-1.)
    lightPos2 = (2.,3.,1.,-1.)
    
    glLightfv(GL_LIGHT0, GL_POSITION, lightPos0)
    glLightfv(GL_LIGHT1, GL_POSITION, lightPos1)
    glLightfv(GL_LIGHT2, GL_POSITION, lightPos2)
    glPopMatrix()

    # Intensidad de color de luz
    ambientLightColor0 = (.2,.1,0.3,1.)
    diffuseLightColor0 = (1.,1.,1.,1.)
    specularLightColor0 = (1.,1.,1.,1.)

    ambientLightColor1 = (.075,.075,.075,1.)
    diffuseLightColor1 = (0.75,0.75,0.75,0.75)
    specularLightColor1 = (0.75,0.75,0.75,0.75)

    ambientLightColor2 = (.05,.05,.05,1.)
    diffuseLightColor2 = (0.5,0.5,0.,0.5)
    specularLightColor2 = (0.5,0.5,0.,0.5)

    glLightfv(GL_LIGHT0, GL_AMBIENT, ambientLightColor0)
    glLightfv(GL_LIGHT0, GL_DIFFUSE, diffuseLightColor0)
    glLightfv(GL_LIGHT0, GL_SPECULAR, specularLightColor0)
    glLightfv(GL_LIGHT1, GL_AMBIENT, ambientLightColor1)
    glLightfv(GL_LIGHT1, GL_DIFFUSE, diffuseLightColor1)
    glLightfv(GL_LIGHT1, GL_SPECULAR, specularLightColor1)
    glLightfv(GL_LIGHT2, GL_AMBIENT, ambientLightColor2)
    glLightfv(GL_LIGHT2, GL_DIFFUSE, diffuseLightColor2)
    glLightfv(GL_LIGHT2, GL_SPECULAR, specularLightColor2)

    # material reflectance for each color channel
    diffuseObjectColor = (0.4,0.6,0.5,1.)
    specularObjectColor = (0.6,0.3,0.3,.5)

    glMaterialfv(GL_FRONT, GL_AMBIENT_AND_DIFFUSE, diffuseObjectColor)
    #glMaterialfv(GL_FRONT, GL_SPECULAR, specularObjectColor)

    glPushMatrix()
    if dropped == 1:
        draw_glDrawArray()
    glPopMatrix()

    glBindTexture(GL_TEXTURE_2D, 0)
    glBindTexture(GL_TEXTURE_2D, 0)
    glDisable(GL_LIGHTING)
    
def draw_glDrawArray():
    global gVertexArraySeparate
    varr = gVertexArraySeparate
    glEnableClientState(GL_VERTEX_ARRAY)
    glEnableClientState(GL_NORMAL_ARRAY)
    glEnableClientState(GL_TEXTURE_COORD_ARRAY)
    glTexCoordPointer(2, GL_FLOAT, 6 * varr.itemsize, ctypes.c_void_p(varr.ctypes.data + 3 * varr.itemsize))  # Set texture coordinates
    glNormalPointer(GL_FLOAT, 6*varr.itemsize, varr)
    glVertexPointer(3, GL_FLOAT, 6*varr.itemsize, ctypes.c_void_p(varr.ctypes.data + 3*varr.itemsize))
    glDrawArrays(GL_TRIANGLES, 0, int(varr.size/6))
    glDisableClientState(GL_TEXTURE_COORD_ARRAY)  # Disable texture coordinate array

def drawFrame():
    glBegin(GL_LINES)
    glColor3ub(255, 0, 0)
    glVertex3fv(np.array([0.,0.,0.]))
    glVertex3fv(np.array([1.,0.,0.]))
    glColor3ub(0, 255, 0)
    glVertex3fv(np.array([0.,0.,0.]))
    glVertex3fv(np.array([0.,1.,0.]))
    glColor3ub(0, 0, 255)
    glVertex3fv(np.array([0.,0.,0]))
    glVertex3fv(np.array([0.,0.,1.]))
    glEnd()

def key_callback(window, key, scancode, action, mods):
    global gCamAng, gCamHeight, modeFlag, distanceFromOrigin
    if action==glfw.PRESS or action==glfw.REPEAT:
        if key==glfw.KEY_1:
            gCamAng += np.radians(-10%360)
        elif key==glfw.KEY_3:
            gCamAng += np.radians(10%360)
        elif key==glfw.KEY_2:
            if gCamHeight < 9:
                gCamHeight += .1
        elif key==glfw.KEY_W:
            if gCamHeight > -9:
                gCamHeight += -.1
        elif key==glfw.KEY_Z:
            if modeFlag == 0:
                glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
                modeFlag = 1
            else:
                glPolygonMode(GL_FRONT_AND_BACK,GL_FILL)
                modeFlag = 0
        elif key==glfw.KEY_A:
            if distanceFromOrigin > 0:
                distanceFromOrigin -= 1
        elif key==glfw.KEY_S:
            if distanceFromOrigin < 180:
                distanceFromOrigin +=1
        elif key==glfw.KEY_V:
            gCamAng = 0.
            gCamHeight = 1.
            distanceFromOrigin = 45
gVertexArraySeparate = np.zeros((3, 3))


def main(obj_path):
    global gVertexArraySeparate, gCursorXPos, gCursorYPos
    if not glfw.init():
        return
    
    window = glfw.create_window(1280,1280,'Graficador de obj 3D', None,None)
    if not window:
        glfw.terminate()
        return
    glfw.make_context_current(window)
    load_texture(texture_path)  # Load the texture
    glfw.set_key_callback(window, key_callback)
    glfw.set_cursor_pos_callback(window, cursor_pos_callback)
    glfw.set_mouse_button_callback(window, mouse_button_callback)
    glfw.set_scroll_callback(window, scroll_callback)
    glfw.set_framebuffer_size_callback(window, framebuffer_size_callback)

    dropCallback(window, [obj_path])

    #glfw.set_drop_callback(window, dropCallback)

    glfw.swap_interval(1)
    count = 0
    while not glfw.window_should_close(window):
        glfw.poll_events()
        count+=1
        ang = count % 360
        render(ang)
        count += 1
        glfw.swap_buffers(window)
    glfw.terminate()
def l2norm(v):
    return np.sqrt(np.dot(v, v))
def normalized(v):
    l = l2norm(v)
    return 1/l * np.array(v)

def framebuffer_size_callback(window, width, height):
    glViewport(0, 0, width, height)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python script.py obj_path")
    else:
        main(sys.argv[1])
			

from mpl_toolkits import mplot3d
import numpy as np
import math
from math import *
from inputs import get_gamepad
import threading
import matplotlib.pyplot as plt
import serial
import pygame
import time
ser = serial.Serial('COM4', 11500)
 

# Function to send command to Arduino
def send_command(axis, angle):
    if angle > 180:
        angle = 180
    if angle < 0:
        angle = 0
    command = axis + str(angle) + '\n'

    ser.write(command.encode())
    print(command.encode())

def setupView(limit):
    ax = plt.axes(projection="3d")
    ax.set_xlim(-limit, limit)
    ax.set_ylim(-limit, limit)
    ax.set_zlim(-limit, limit)
    ax.set_xlabel("X")
    ax.set_ylabel("Z")
    ax.set_zlabel("Y")
    return ax

#%matplotlib notebook LEG INVERSE KINEMATICS:

setupView(110).view_init(elev=20., azim=135)

fig = plt.figure()

omega =  pi/4
phi =0
psi = 0

xm = 0
ym = 0
zm = 0

l1=25
l2=20
l3=80
l4=80

L = 120
W = 90

Lp=np.array([[100,-100,100,1],[100,-100,-100,1],[-100,-100,100,1],[-100,-100,-100,1]])

sHp=np.sin(pi/2)
cHp=np.cos(pi/2)

Lo=np.array([0,0,0,1])

def bodyIK(omega,phi,psi,xm,ym,zm):
    Rx = np.array([[1,0,0,0],
                   [0,np.cos(omega),-np.sin(omega),0],
                   [0,np.sin(omega),np.cos(omega),0],[0,0,0,1]])
    Ry = np.array([[np.cos(phi),0,np.sin(phi),0],
                   [0,1,0,0],
                   [-np.sin(phi),0,np.cos(phi),0],[0,0,0,1]])
    Rz = np.array([[np.cos(psi),-np.sin(psi),0,0],
                   [np.sin(psi),np.cos(psi),0,0],[0,0,1,0],[0,0,0,1]])
    Rxyz=Rx@Ry@Rz

    T = np.array([[0,0,0,xm],[0,0,0,ym],[0,0,0,zm],[0,0,0,0]])
    Tm = T+Rxyz

    return([Tm @ np.array([[cHp,0,sHp,L/2],[0,1,0,0],[-sHp,0,cHp,W/2],[0,0,0,1]]),
           Tm @ np.array([[cHp,0,sHp,L/2],[0,1,0,0],[-sHp,0,cHp,-W/2],[0,0,0,1]]),
           Tm @ np.array([[cHp,0,sHp,-L/2],[0,1,0,0],[-sHp,0,cHp,W/2],[0,0,0,1]]),
           Tm @ np.array([[cHp,0,sHp,-L/2],[0,1,0,0],[-sHp,0,cHp,-W/2],[0,0,0,1]])
           ])

# Initialize last_angles with some default values
last_angles = [0, 0, 0]

def legIK(point):
    global last_angles  # This allows us to modify last_angles inside this function
    try:
        (x,y,z)=(point[0],point[1],point[2])
        F=sqrt(x**2+y**2-l1**2)
        G=F-l2  
        H=sqrt(G**2+z**2)
        theta1=-atan2(y,x)-atan2(F,-l1)

        D=(H**2-l3**2-l4**2)/(2*l3*l4)
        if D < -1 or D > 1:
            print("Point is not reachable")
            return None
        theta3=acos(D) 

        theta2=atan2(z,G)-atan2(l4*sin(theta3),l3+l4*cos(theta3))
        
        angles = [theta1, theta2, theta3]
        return angles
    except Exception as e:
        print(f"An error occurred: {e}")
        return None



    #angles_deg = [math.degrees(angle) for angle in angles] # Convert angles from radians to degrees
    #angles_deg = [max(min(180, angle), 0) for angle in angles_deg] # Ensure the angles are within the range 0-180
    #angles_csv = ','.join(map(str, angles_deg)) # Convert angles to CSV format
    #ser.write(angles_csv.encode()) # Write to serial port
    

def calcLegPoints(angles):
    (theta1,theta2,theta3)=angles
    theta23=theta2+theta3

    T0=Lo
    T1=T0+np.array([-l1*cos(theta1),l1*sin(theta1),0,0])
    T2=T1+np.array([-l2*sin(theta1),-l2*cos(theta1),0,0])
    T3=T2+np.array([-l3*sin(theta1)*cos(theta2),-l3*cos(theta1)*cos(theta2),l3*sin(theta2),0])
    T4=T3+np.array([-l4*sin(theta1)*cos(theta23),-l4*cos(theta1)*cos(theta23),l4*sin(theta23),0])

    return np.array([T0,T1,T2,T3,T4])

def drawLegPoints(p):
    plt.plot([x[0] for x in p],[x[2] for x in p],[x[1] for x in p], 'k-', lw=3)
    plt.plot([p[0][0]],[p[0][2]],[p[0][1]],'bo',lw=2)
    plt.plot([p[4][0]],[p[4][2]],[p[4][1]],'ro',lw=2)    

def drawLegPair(Tl,Tr,Ll,Lr):
    Ix=np.array([[-1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]])
    drawLegPoints([Tl@x for x in calcLegPoints(legIK(np.linalg.inv(Tl)@Ll))])
    drawLegPoints([Tr@Ix@x for x in calcLegPoints(legIK(Ix@np.linalg.inv(Tr)@Lr))])

def drawRobot(Lp,angles,center):
    (omega,phi,psi)=angles
    (xm,ym,zm)=center

    FP=[0,0,0,1]
    (Tlf,Trf,Tlb,Trb)= bodyIK(omega,phi,psi,xm,ym,zm)
    CP=[x@FP for x in [Tlf,Trf,Tlb,Trb]]

    CPs=[CP[x] for x in [0,1,3,2,0]]
    plt.plot([x[0] for x in CPs],[x[2] for x in CPs],[x[1] for x in CPs], 'bo-', lw=2)

    drawLegPair(Tlf,Trf,Lp[0],Lp[1])
    drawLegPair(Tlb,Trb,Lp[2],Lp[3])
    print(Tlf,Tlb,Trb)
    
pygame.init()

# Initialize the joystick
joystick = pygame.joystick.Joystick(0)
joystick.init()

fig = plt.figure()


while True:
    # Process events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()  # Quit pygame
            quit()  # Quit the program

    # Read the analog stick values
    A = joystick.get_axis(0)  # Left stick horizontal (left is -1, right is 1)
    y = joystick.get_axis(1)  # Left stick vertical (up is -1, down is 1)
    x = joystick.get_axis(2)  # Right stick horizontal (left is -1, right is 1)
    C = joystick.get_axis(3)  # Right stick vertical (up is -1, down is 1)
    z = joystick.get_hat(0)[0]  # D-pad horizontal (left is -1, right is 1)
    B = joystick.get_hat(0)[1]  # D-pad vertical (up is 1, down is -1)


    print(A, B, C, x, y, z)

    # Calculate body positions for each leg
    (Tlf, Trf, Tlb, Trb) = bodyIK(A, B, C, x, y, z)
    #print(Tlf, Trf,'angles0.0')
    

    # Calculate leg points for each leg
    leg_points = [np.linalg.inv(T) @ L for T, L in zip([Tlf, Trf, Tlb, Trb], Lp)]

    angles_out = []  # Initialize an empty list

    for point in leg_points:
        angles = legIK(point) 
        if angles is not None:  # Only extend if angles is not None
            angles_out.extend(angles)

    # Normalize angles and convert to degrees
    angles_deg = [int((math.degrees(angle))) for angle in angles_out]
    
    print(angles_deg)
    # Check if angles_deg has exactly 12 values
    if len(angles_deg) == 12:
        # Convert all angles to CSV format
        send_command('A', angles_deg[0]+74) 
        send_command('B', angles_deg[1]+117)
        send_command('C', angles_deg[2]-12)
        send_command('D', angles_deg[3]+131)
        send_command('E', angles_deg[4]+117)
        send_command('F', angles_deg[5]-12)
        send_command('G', angles_deg[6]+74)
        send_command('H', angles_deg[7]+117)
        send_command('I', angles_deg[8]-12)
        send_command('J', angles_deg[9]+131)
        send_command('K', angles_deg[10]+165)
        send_command('L', angles_deg[11]-12)


    # Print all the angles
        #print(angles_out)
    else:
        print("Error: Expected 12 angles, but got " + str(len(angles_out)))
    # Clear the current plot
    plt.clf()

    # Set up the view
    ax = setupView(110)
    ax.view_init(elev=20., azim=135)

    # Draw the robot
    drawRobot(Lp, (A, B, C), (x, y, z))

    # Redraw the plot
    plt.draw()
    plt.pause(0.001)


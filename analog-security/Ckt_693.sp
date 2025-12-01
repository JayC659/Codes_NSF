*SPICE Netlist for circuit 693
.include '/home/jchaudh3/DAWN_work/Netlist/cmi49.inc'
.model pmos pmos level=49
.model nmos nmos level=49
.param VD = 2.5
.param VD2 = 'VD/2'
.param dc_step = 0.1
.param Vin = 'VD'
C1 2 0 1nF
C2 7 0 1nF
M6 7 4 8 10 PMOS W=1u L=1u
I1 1 0 DC 1mA
M2 9 3 1 0 NMOS W=1u L=1u
M4 2 4 10 0 PMOS W=1u L=1u
M1 2 5 9 9 NMOS W=1u L=1u
M3 10 6 VDD VDD PMOS W=1u L=1u
M5 8 6 5 VDD PMOS W=1u L=1u
V1 VDD 0 VD
V2 2 0 Vin
.DC Vin 0 VD dc_step
.print V(0) V(1) V(2) V(3) V(4) V(5) V(6) V(7) V(8) V(9) V(10)
.OP
.END


v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
C {symbols/pfet_03v3.sym} 200 120 0 0 {name=MP_rco L=20u W=1u nf=1 m=1 model=pfet_03v3 spiceprefix=X}
C {devices/lab_pin.sym} 220 150 0 0 {name=l1 sig_type=std_logic lab=tco}
C {devices/lab_pin.sym} 180 120 2 0 {name=l2 sig_type=std_logic lab=VSS}
C {devices/lab_pin.sym} 220 90 0 0 {name=l3 sig_type=std_logic lab=VDD}
C {devices/lab_pin.sym} 220 120 0 0 {name=l4 sig_type=std_logic lab=VDD}
C {symbols/cap_nmos_03v3.sym} 360 120 0 0 {name=C_tco W=30u L=30u model=cap_nmos_03v3 spiceprefix=X m=1}
C {devices/lab_pin.sym} 360 90 3 0 {name=l5 sig_type=std_logic lab=tco}
C {devices/lab_pin.sym} 360 150 1 0 {name=l6 sig_type=std_logic lab=VSS}
C {symbols/pfet_03v3.sym} 200 270 0 0 {name=MP_ico L=0.28u W=5u nf=1 m=1 model=pfet_03v3 spiceprefix=X}
C {devices/lab_pin.sym} 220 300 0 0 {name=l7 sig_type=std_logic lab=gco}
C {devices/lab_pin.sym} 180 270 2 0 {name=l8 sig_type=std_logic lab=tco}
C {devices/lab_pin.sym} 220 240 0 0 {name=l9 sig_type=std_logic lab=VDD}
C {devices/lab_pin.sym} 220 270 0 0 {name=l10 sig_type=std_logic lab=VDD}
C {symbols/nfet_03v3.sym} 360 270 0 0 {name=MN_ico L=0.28u W=8u nf=1 m=1 model=nfet_03v3 spiceprefix=X}
C {devices/lab_pin.sym} 380 240 0 0 {name=l11 sig_type=std_logic lab=gco}
C {devices/lab_pin.sym} 340 270 2 0 {name=l12 sig_type=std_logic lab=tco}
C {devices/lab_pin.sym} 380 300 0 0 {name=l13 sig_type=std_logic lab=VSS}
C {devices/lab_pin.sym} 380 270 0 0 {name=l14 sig_type=std_logic lab=VSS}
C {symbols/nfet_03v3.sym} 520 195 0 0 {name=MN_clampco L=0.8u W=400u nf=40 m=1 model=nfet_03v3 spiceprefix=X}
C {devices/lab_pin.sym} 540 165 0 0 {name=l15 sig_type=std_logic lab=VDD}
C {devices/lab_pin.sym} 500 195 2 0 {name=l16 sig_type=std_logic lab=gco}
C {devices/lab_pin.sym} 540 225 0 0 {name=l17 sig_type=std_logic lab=VSS}
C {devices/lab_pin.sym} 540 195 0 0 {name=l18 sig_type=std_logic lab=VSS}
T {core-supply pad: VDD/VSS rail clamp, RC-triggered nfet_03v3 (spec/decisions/0003). DVDD/DVSS pass through.} 20 10 0 0 0.4 0.4 {}
C {devices/iopin.sym} 20 60 0 0 {name=p19 lab=DVDD}
C {devices/iopin.sym} 20 90 0 0 {name=p20 lab=DVSS}
C {devices/iopin.sym} 20 120 0 0 {name=p21 lab=VDD}
C {devices/iopin.sym} 20 150 0 0 {name=p22 lab=VSS}

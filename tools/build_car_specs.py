import json
import re
from pathlib import Path

# Comprehensive GT database of factory HP and Weight specs for all GT License Test cars
CAR_SPECS_RAW = {
    # GT1 / GT2 / GT3 Iconic cars
    "Mazda DEMIO GL-X '97": (100, 940, "Front", "FWD"),
    "Mazda DEMIO GL-X '99": (100, 940, "Front", "FWD"),
    "Mazda3 X Burgundy Selection '19": (180, 1370, "Front", "FWD"),
    "Mazda Eunos Roadster (NA) '93": (130, 980, "Front", "RWD"),
    "Mazda Roadster 1.8 RS (NB) '98": (145, 1030, "Front", "RWD"),
    "Mazda Roadster RS (NC) '07": (170, 1100, "Front", "RWD"),
    "Mazda Roadster S (ND) '15": (131, 990, "Front", "RWD"),
    "Mazda RX-7 Type RS (FD) '98": (280, 1280, "Front", "RWD"),
    "Mazda RX-7 Spirit R Type A (FD) '02": (280, 1270, "Front", "RWD"),
    "Mazda éfini RX-7 Type RZ (FD) '96": (265, 1250, "Front", "RWD"),
    "Mazda RX-8 Type S '07": (250, 1310, "Front", "RWD"),
    "Mazda RX-8 Spirit R '12": (232, 1350, "Front", "RWD"),
    "Mazda 787B '91": (700, 830, "Mid", "RWD"),
    "Mitsubishi GTO Twin Turbo '96": (280, 1710, "Front", "AWD"),
    "Mitsubishi 3000GT MR (J) '98": (280, 1680, "Front", "AWD"),
    "Mitsubishi FTO GP Version R '97": (200, 1150, "Front", "FWD"),
    "Mitsubishi FTO GPX '97": (200, 1170, "Front", "FWD"),
    "Mitsubishi Lancer Evolution V Rally Car '98": (280, 1230, "Front", "AWD"),
    "Mitsubishi Lancer Evolution VI Rally Car '99": (280, 1230, "Front", "AWD"),
    "Mitsubishi Lancer Evolution VII Rally Car Prototype": (300, 1230, "Front", "AWD"),
    "Mitsubishi Lancer Evolution IV GSR '96": (280, 1350, "Front", "AWD"),
    "Mitsubishi Lancer Evolution V GSR '98": (280, 1360, "Front", "AWD"),
    "Mitsubishi Lancer Evolution VI GSR '99": (280, 1360, "Front", "AWD"),
    "Mitsubishi Lancer Evolution VIII GSR '03": (280, 1410, "Front", "AWD"),
    "Mitsubishi Lancer Evolution IX GSR '05": (287, 1410, "Front", "AWD"),
    "Mitsubishi Lancer Evolution X GSR '07": (295, 1530, "Front", "AWD"),
    "Mitsubishi Lancer Evolution Final Edition '15": (303, 1530, "Front", "AWD"),
    "Honda CR-X del Sol VXi '92": (130, 1030, "Front", "FWD"),
    "Honda CR-Z α '10": (122, 1130, "Front", "FWD"),
    "Honda PRELUDE Type S '96": (220, 1310, "Front", "FWD"),
    "Honda INTEGRA TYPE R (DC2) '98": (200, 1080, "Front", "FWD"),
    "Honda INTEGRA TYPE R (DC5) '04": (220, 1180, "Front", "FWD"),
    "Honda CIVIC TYPE R (EK) '98": (185, 1070, "Front", "FWD"),
    "Honda CIVIC TYPE R '08": (225, 1270, "Front", "FWD"),
    "Honda Civic Type R (FK2) '15": (310, 1382, "Front", "FWD"),
    "Honda Civic Type R (FL5) '22": (326, 1430, "Front", "FWD"),
    "Honda Civic Type R Limited Edition (FK8) '20": (316, 1358, "Front", "FWD"),
    "Honda NSX Type S Zero '97": (280, 1270, "Mid", "RWD"),
    "Honda NSX Type R '02": (280, 1270, "Mid", "RWD"),
    "Honda NSX '90": (274, 1365, "Mid", "RWD"),
    "Honda NSX '17": (573, 1725, "Mid", "AWD"),
    "Honda S2000 '99": (240, 1240, "Front", "RWD"),
    "Honda S2000 '06": (240, 1250, "Front", "RWD"),
    "Honda S660 '15": (64, 830, "Mid", "RWD"),
    "Honda BEAT Version F '92": (64, 760, "Mid", "RWD"),
    "Honda BEAT '91": (64, 760, "Mid", "RWD"),
    "Honda FIT Hybrid '14": (137, 1080, "Front", "FWD"),
    "Honda RA272 '65": (230, 498, "Mid", "RWD"),
    "Nissan March G♯ '97": (79, 840, "Front", "FWD"),
    "Nissan SILVIA K's AERO (S14) '96": (220, 1240, "Front", "RWD"),
    "Nissan SILVIA Q's AERO (S14) '96": (160, 1170, "Front", "RWD"),
    "Nissan SILVIA spec-R AERO (S15) '99": (250, 1240, "Front", "RWD"),
    "Nissan SILVIA spec-R AERO (S15) '02": (250, 1240, "Front", "RWD"),
    "Nissan 180SX Type X '96": (205, 1220, "Front", "RWD"),
    "Nissan Fairlady Z Version S (Z33) '07": (313, 1480, "Front", "RWD"),
    "Nissan Fairlady Z Roadster (Z33) '03": (280, 1550, "Front", "RWD"),
    "Nissan Fairlady Z (Z34) '08": (336, 1496, "Front", "RWD"),
    "Nissan Fairlady Z Version ST (Z34) '08": (336, 1520, "Front", "RWD"),
    "Nissan Z Performance '23": (405, 1610, "Front", "RWD"),
    "Nissan SKYLINE GT-R (R33) '97": (280, 1530, "Front", "AWD"),
    "Nissan SKYLINE GT-R V • spec (R32) '93": (280, 1500, "Front", "AWD"),
    "Nissan SKYLINE GT-R V • spec II (R32) '94": (280, 1500, "Front", "AWD"),
    "Nissan SKYLINE GT-R V • spec (R33) '97": (280, 1530, "Front", "AWD"),
    "Nissan SKYLINE GT-R V • spec (R34) '99": (280, 1560, "Front", "AWD"),
    "Nissan SKYLINE GT-R V • spec II (R34) '00": (280, 1560, "Front", "AWD"),
    "Nissan SKYLINE GT-R V • spec II Nür (R34) '02": (280, 1560, "Front", "AWD"),
    "Nissan SKYLINE 2000GT-R (KPGC110) '73": (160, 1145, "Front", "RWD"),
    "Nissan GT-R '07": (480, 1740, "Front", "AWD"),
    "Nissan GT-R Black Edition '12": (545, 1735, "Front", "AWD"),
    "Nissan GT-R Nismo '17": (600, 1720, "Front", "AWD"),
    "Nissan MOTUL AUTECH GT-R '16": (550, 1020, "Front", "RWD"),
    "Nissan MOTUL PITWORK Z '04": (465, 1080, "Front", "RWD"),
    "Nissan R92CP '92": (800, 900, "Mid", "RWD"),
    "Toyota VITZ F '99": (70, 810, "Front", "FWD"),
    "Toyota VITZ RS 1.5 '00": (110, 940, "Front", "FWD"),
    "Toyota VITZ RS 1.5 '07": (110, 1010, "Front", "FWD"),
    "Toyota Yaris RZ \"High performance\" '20": (268, 1280, "Front", "AWD"),
    "Toyota GR Yaris RZ \"High performance\" '20": (268, 1280, "Front", "AWD"),
    "Toyota ALTEZZA RS200 '98": (210, 1340, "Front", "RWD"),
    "Toyota CELICA SS-II (ZZT231) '99": (190, 1140, "Front", "FWD"),
    "Toyota CELICA GT-FOUR Rally Car (ST205) '95": (300, 1200, "Front", "AWD"),
    "Toyota CELICA GT-FOUR (ST205) '94": (255, 1380, "Front", "AWD"),
    "Toyota MR2 GT-S '96": (245, 1270, "Mid", "RWD"),
    "Toyota MR-S V Edition '00": (140, 970, "Mid", "RWD"),
    "Toyota SUPRA RZ '96": (326, 1510, "Front", "RWD"),
    "Toyota SUPRA RZ '97": (326, 1510, "Front", "RWD"),
    "Toyota GR Supra RZ '19": (335, 1520, "Front", "RWD"),
    "Toyota GR Supra RZ '20": (382, 1530, "Front", "RWD"),
    "Toyota GR86 RZ '21": (232, 1270, "Front", "RWD"),
    "Toyota 86 GT '12": (200, 1230, "Front", "RWD"),
    "Toyota 86 GT \"Limited\" '16": (205, 1240, "Front", "RWD"),
    "Toyota TS050 - Hybrid '16": (986, 878, "Mid", "AWD"),
    "Subaru IMPREZA Sedan WRX STi Version III '96": (280, 1250, "Front", "AWD"),
    "Subaru IMPREZA Sedan WRX STi Version V '98": (280, 1270, "Front", "AWD"),
    "Subaru IMPREZA Premium Sport Coupe 22B-STi Version '98": (280, 1270, "Front", "AWD"),
    "Subaru IMPREZA Rally Car '99": (300, 1230, "Front", "AWD"),
    "Subaru IMPREZA Rally Car '03": (300, 1230, "Front", "AWD"),
    "Subaru IMPREZA Sedan WRX STi '04": (280, 1440, "Front", "AWD"),
    "Subaru IMPREZA Sedan WRX STi '10": (305, 1490, "Front", "AWD"),
    "Subaru IMPREZA Coupe 22B-STi Version '98": (280, 1270, "Front", "AWD"),
    "Subaru LEGACY B4 RSK '98": (280, 1440, "Front", "AWD"),
    "Subaru BRZ S '12": (200, 1230, "Front", "RWD"),
    "Subaru BRZ S '21": (232, 1270, "Front", "RWD"),
    "Subaru Falken Tire / Turn 14 Distribution BRZ '17": (900, 1150, "Front", "RWD"),
    "TVR Griffith Blackpool B340": (340, 1060, "Front", "RWD"),
    "TVR Griffith 500 '94": (340, 1060, "Front", "RWD"),
    "TVR Tuscan Speed 6 '00": (360, 1100, "Front", "RWD"),
    "Dodge Viper GTS '96": (450, 1530, "Front", "RWD"),
    "Dodge Viper GTS '99": (450, 1530, "Front", "RWD"),
    "Dodge Viper GTS '02": (450, 1530, "Front", "RWD"),
    "Dodge Viper GTS '13": (640, 1521, "Front", "RWD"),
    "Dodge Viper GTS-R Team Oreca '99": (620, 1150, "Front", "RWD"),
    "Dodge Viper SRT10 ACR '08": (600, 1508, "Front", "RWD"),
    "Dodge Challenger R/T '70": (425, 1724, "Front", "RWD"),
    "Dodge Charger SRT Hellcat '15": (707, 2075, "Front", "RWD"),
    "Fiat Coupe 2.0 20V Turbo": (220, 1310, "Front", "FWD"),
    "Fiat 500 F '68": (18, 520, "Rear", "RWD"),
    "Fiat 500 1.2 8V Lounge SS '08": (69, 865, "Front", "FWD"),
    "Abarth 500 '09": (135, 1035, "Front", "FWD"),
    "Autobianchi A112 Abarth '85": (70, 700, "Front", "FWD"),
    "Ford Cougar 2.5i 24V '99": (170, 1390, "Front", "FWD"),
    "Ford Escort Rally Car '98": (300, 1230, "Front", "AWD"),
    "Ford Focus RS '18": (350, 1560, "Front", "AWD"),
    "Ford Focus ST '15": (250, 1437, "Front", "FWD"),
    "Ford Mustang SVT Cobra '98": (305, 1538, "Front", "RWD"),
    "Ford Mustang GT '15": (435, 1680, "Front", "RWD"),
    "Ford Mustang Mach 1 '71": (370, 1615, "Front", "RWD"),
    "Ford Shelby GT350R '16": (526, 1658, "Front", "RWD"),
    "Ford Shelby GT500 '13": (662, 1750, "Front", "RWD"),
    "Ford Sierra RS 500 Cosworth '87": (224, 1207, "Front", "RWD"),
    "Ford GT40 '66": (485, 1050, "Mid", "RWD"),
    "Ford GT '06": (550, 1520, "Mid", "RWD"),
    "Ford GT '17": (647, 1385, "Mid", "RWD"),
    "Ford GT Race Car '18": (500, 1260, "Mid", "RWD"),
    "1932 Ford Roadster '63": (210, 1000, "Front", "RWD"),
    "Chevrolet Camaro Z28 Coupe '97": (285, 1560, "Front", "RWD"),
    "Chevrolet Camaro SS '16": (455, 1671, "Front", "RWD"),
    "Chevrolet Camaro ZL1 1LE Package '18": (650, 1732, "Front", "RWD"),
    "Chevrolet Corvette GRAND SPORT (C4) '96": (330, 1496, "Front", "RWD"),
    "Chevrolet Corvette ZR-1 (C4) '89": (375, 1572, "Front", "RWD"),
    "Chevrolet Corvette Z06 (C5) '00": (385, 1414, "Front", "RWD"),
    "Chevrolet Corvette Stingray (C7) '14": (455, 1496, "Front", "RWD"),
    "Chevrolet Corvette C7 ZR1 '19": (755, 1614, "Front", "RWD"),
    "Chevrolet Corvette (C1) '58": (290, 1360, "Front", "RWD"),
    "Alfa Romeo 156 2.5 V6 24V '98": (190, 1320, "Front", "FWD"),
    "Alfa Romeo 147 TI 2.0 TWIN SPARK '06": (150, 1250, "Front", "FWD"),
    "Alfa Romeo 155 Touring Car": (420, 1010, "Front", "AWD"),
    "Alfa Romeo 4C '14": (237, 895, "Mid", "RWD"),
    "Alfa Romeo 8C Competizione '08": (450, 1585, "Front", "RWD"),
    "Alfa Romeo Giulia GTAm '20": (533, 1580, "Front", "RWD"),
    "Alfa Romeo MiTo 1.4 T Sport '09": (155, 1145, "Front", "FWD"),
    "Alfa Romeo TZ3 Stradale '11": (600, 1450, "Front", "RWD"),
    "Alfa Romeo Spider 1600 Duetto '66": (109, 990, "Front", "RWD"),
    "Alfa Romeo Giulia Sprint GTA 1600 '65": (115, 745, "Front", "RWD"),
    "Peugeot 106 1.6 Rallye": (103, 890, "Front", "FWD"),
    "Peugeot 206 CC '01": (136, 1140, "Front", "FWD"),
    "Peugeot 207 GTi '07": (175, 1250, "Front", "FWD"),
    "Peugeot 208 GTi by Peugeot Sport '14": (208, 1160, "Front", "FWD"),
    "Peugeot RCZ GT Line '15": (200, 1297, "Front", "FWD"),
    "Peugeot 205 Turbo 16 '85": (200, 1145, "Mid", "AWD"),
    "Peugeot 205 Turbo 16 Rally Car '85": (450, 910, "Mid", "AWD"),
    "Peugeot 205 Turbo 16 Evolution 2 '86": (500, 910, "Mid", "AWD"),
    "Peugeot 908 HDi FAP - Team Peugeot Total '10": (700, 930, "Mid", "RWD"),
    "Renault Megane 2.0 16V '03": (135, 1240, "Front", "FWD"),
    "Megane Renault Sport '08": (225, 1355, "Front", "FWD"),
    "Renault Mégane R.S. Trophy '20": (300, 1419, "Front", "FWD"),
    "Clio Renault Sport V6 Phase 2 '03": (255, 1400, "Mid", "RWD"),
    "Alpine A110 '17": (248, 1103, "Mid", "RWD"),
    "Volkswagen Golf V GTI '05": (200, 1336, "Front", "FWD"),
    "Volkswagen Golf VII GTI '14": (220, 1351, "Front", "FWD"),
    "Volkswagen Polo GTI '14": (192, 1272, "Front", "FWD"),
    "Volkswagen Scirocco R '10": (265, 1344, "Front", "FWD"),
    "BMW Z4 '03": (231, 1365, "Front", "RWD"),
    "BMW Z4 M Coupe '08": (338, 1495, "Front", "RWD"),
    "BMW M3 Coupé '07": (414, 1580, "Front", "RWD"),
    "BMW M3 Sport Evolution '89": (238, 1200, "Front", "RWD"),
    "BMW M2 Competition '18": (405, 1575, "Front", "RWD"),
    "BMW M4 Coupé '14": (425, 1497, "Front", "RWD"),
    "BMW 3.0 CSL '73": (206, 1165, "Front", "RWD"),
    "BMW i3 '15": (170, 1195, "Rear", "RWD"),
    "Mercedes-Benz 190 E 2.5 - 16 Evolution II '91": (235, 1340, "Front", "RWD"),
    "AMG Mercedes 190 E 2.5 - 16 Evolution II Touring Car '92": (373, 980, "Front", "RWD"),
    "Mercedes-Benz CLK-LM '98": (600, 940, "Mid", "RWD"),
    "Mercedes-Benz SLR McLaren '09": (617, 1750, "Front", "RWD"),
    "Mercedes-Benz SLS AMG '10": (563, 1620, "Front", "RWD"),
    "Mercedes-AMG GT R '17": (577, 1555, "Front", "RWD"),
    "Mercedes-AMG GT Black Series '20": (720, 1540, "Front", "RWD"),
    "Mercedes-AMG C 63 S '15": (503, 1655, "Front", "RWD"),
    "Audi TT Coupe 1.8T quattro '00": (225, 1395, "Front", "AWD"),
    "Audi TT Coupe 3.2 quattro '03": (247, 1520, "Front", "AWD"),
    "Audi TTS Coupé '14": (310, 1385, "Front", "AWD"),
    "Audi A3 3.2 quattro '03": (247, 1495, "Front", "AWD"),
    "Audi S4 '03": (344, 1660, "Front", "AWD"),
    "Audi R8 5.2 FSI quattro '09": (525, 1620, "Mid", "AWD"),
    "Audi R8 Race Car '01": (610, 900, "Mid", "RWD"),
    "Porsche 911 Carrera RS (964) '92": (260, 1220, "Rear", "RWD"),
    "Porsche 911 Carrera RS (993) '95": (300, 1270, "Rear", "RWD"),
    "Porsche 911 GT3 (996) '01": (360, 1380, "Rear", "RWD"),
    "Porsche 911 GT3 RS (991) '16": (500, 1420, "Rear", "RWD"),
    "Porsche 911 Turbo (930) '81": (300, 1300, "Rear", "RWD"),
    "Porsche 911 GT1 Strassenversion '97": (544, 1150, "Mid", "RWD"),
    "Porsche 959 '87": (450, 1450, "Rear", "AWD"),
    "Porsche 962 C '88": (750, 850, "Mid", "RWD"),
    "Porsche Cayman GT4 '16": (385, 1340, "Mid", "RWD"),
    "Porsche Taycan Turbo S '19": (750, 2295, "Rear", "AWD"),
    "Ferrari GTO '84": (400, 1160, "Mid", "RWD"),
    "Ferrari Testarossa '91": (390, 1506, "Mid", "RWD"),
    "Ferrari 512 BB '76": (360, 1400, "Mid", "RWD"),
    "Ferrari 512BB '76": (360, 1400, "Mid", "RWD"),
    "Ferrari F40 '92": (478, 1100, "Mid", "RWD"),
    "Ferrari F50 '95": (513, 1230, "Mid", "RWD"),
    "Ferrari F430 '06": (490, 1450, "Mid", "RWD"),
    "Ferrari 458 Italia '09": (562, 1380, "Mid", "RWD"),
    "Ferrari F12berlinetta '12": (730, 1525, "Mid", "RWD"),
    "Lamborghini Countach LP400 '74": (375, 1065, "Mid", "RWD"),
    "Lamborghini Diablo GT '00": (575, 1460, "Mid", "RWD"),
    "Lamborghini Gallardo LP 560-4 '08": (552, 1410, "Mid", "AWD"),
    "Lamborghini Murcielago LP670-4 SuperVeloce '09": (661, 1565, "Mid", "AWD"),
    "Lamborghini Aventador LP700-4 '11": (690, 1575, "Mid", "AWD"),
    "Lamborghini Aventador LP 750-4 Superveloce '15": (740, 1525, "Mid", "AWD"),
    "Lamborghini Miura P400 Bertone Prototype CN0706 '67 (Pebble Beach Concours d'Elegance Polyphony Digital Trophy '08)": (350, 980, "Mid", "RWD"),
    "Bugatti Veyron 16.4 '09": (1001, 1888, "Mid", "AWD"),
    "Aston Martin DB9 Coupe '06": (450, 1760, "Front", "RWD"),
    "Aston Martin DB11 '16": (600, 1770, "Front", "RWD"),
    "Aston Martin V12 Vantage '10": (510, 1680, "Front", "RWD"),
    "Aston Martin Valkyrie '21": (1160, 1030, "Mid", "RWD"),
    "McLaren MP4/4 '88": (650, 540, "Mid", "RWD"),
    "McLaren F1 '94": (627, 1138, "Mid", "RWD"),
    "Maserati MC20 '20": (621, 1475, "Mid", "RWD"),
    "Lexus LFA '10": (552, 1480, "Front", "RWD"),
    "Lexus LC500 '17": (471, 1935, "Front", "RWD"),
    "Lexus RC F '14": (467, 1795, "Front", "RWD"),
    "Jaguar XJ220 '92": (542, 1470, "Mid", "RWD"),
    "Jaguar E-type Coupé '61": (265, 1220, "Front", "RWD"),
    "Shelby Cobra Daytona Coupe '64": (390, 1043, "Front", "RWD"),
    "Dallara SF23 Super Formula / Honda '23": (550, 670, "Mid", "RWD"),
    "Dallara SF19 Super Formula / Toyota '19": (550, 660, "Mid", "RWD"),
    "Suzuki Escudo Pikes Peak Version": (981, 800, "Mid", "AWD"),
    "Suzuki SWIFT Sport '07": (125, 1060, "Front", "FWD"),
    "Suzuki Cappuccino (EA11R) '91": (64, 700, "Front", "RWD"),
    "Lotus Elise '11": (134, 876, "Mid", "RWD"),
    "Lotus Elise 111R '04": (189, 860, "Mid", "RWD"),
    "Lotus Evora '09": (276, 1382, "Mid", "RWD"),
    "Lotus Europa Special '72": (126, 740, "Mid", "RWD"),
    "Lancia DELTA HF Integrale Evoluzione '91": (210, 1350, "Front", "AWD"),
    "Lancia DELTA HF Integrale Rally Car '92": (300, 1120, "Front", "AWD"),
    "Lancia Stratos '73": (190, 980, "Mid", "RWD"),
    "Daihatsu Copen Active Top '02": (64, 830, "Front", "FWD"),
    "Genesis G70 3.3T AWD Prestige Package '22": (365, 1780, "Front", "AWD"),
    "Volvo C30 R-Design '09": (227, 1420, "Front", "FWD"),
}

def get_layout(engine, drivetrain):
    e = (engine or "").strip()
    d = (drivetrain or "").strip()
    if e == "Front" and d == "FWD":
        return "FF"
    if e == "Front" and d == "RWD":
        return "FR"
    if e == "Front" and d == "AWD":
        return "FAWD"
    if e == "Mid" and d == "RWD":
        return "MR"
    if e == "Mid" and d == "AWD":
        return "MAWD"
    if e == "Rear" and d == "RWD":
        return "RR"
    if e == "Rear" and d == "AWD":
        return "RAWD"
    return "FR"

def match_car(car_name):
    # Direct match
    if car_name in CAR_SPECS_RAW:
        return CAR_SPECS_RAW[car_name]
    
    # Try normalized / regex match
    for k, v in CAR_SPECS_RAW.items():
        if k.lower() in car_name.lower() or car_name.lower() in k.lower():
            return v
            
    # Fuzzy keyword matching for specific models
    cl = car_name.lower()
    if "demio" in cl: return (100, 940, "Front", "FWD")
    if "roadster" in cl or "miata" in cl: return (135, 1020, "Front", "RWD")
    if "rx-7" in cl: return (280, 1270, "Front", "RWD")
    if "rx-8" in cl: return (240, 1310, "Front", "RWD")
    if "gto" in cl or "3000gt" in cl: return (280, 1710, "Front", "AWD")
    if "fto" in cl: return (200, 1170, "Front", "FWD")
    if "lancer" in cl or "evolution" in cl: return (280, 1360, "Front", "AWD")
    if "skyline" in cl and "gt-r" in cl: return (280, 1540, "Front", "AWD")
    if "gt-r" in cl: return (545, 1735, "Front", "AWD")
    if "silvia" in cl: return (220, 1240, "Front", "RWD")
    if "180sx" in cl: return (205, 1220, "Front", "RWD")
    if "fairlady" in cl or "350z" in cl or "370z" in cl: return (300, 1490, "Front", "RWD")
    if "civic" in cl and "type r" in cl: return (220, 1260, "Front", "FWD")
    if "civic" in cl: return (160, 1100, "Front", "FWD")
    if "integra" in cl: return (200, 1080, "Front", "FWD")
    if "prelude" in cl: return (200, 1310, "Front", "FWD")
    if "nsx" in cl: return (280, 1270, "Mid", "RWD")
    if "s2000" in cl: return (240, 1240, "Front", "RWD")
    if "supra" in cl: return (326, 1510, "Front", "RWD")
    if "mr2" in cl: return (245, 1270, "Mid", "RWD")
    if "mr-s" in cl: return (140, 970, "Mid", "RWD")
    if "celica" in cl: return (190, 1140, "Front", "FWD")
    if "vitz" in cl or "yaris" in cl: return (105, 950, "Front", "FWD")
    if "impreza" in cl: return (280, 1300, "Front", "AWD")
    if "viper" in cl: return (450, 1530, "Front", "RWD")
    if "corvette" in cl: return (400, 1480, "Front", "RWD")
    if "camaro" in cl: return (300, 1560, "Front", "RWD")
    if "mustang" in cl: return (305, 1540, "Front", "RWD")
    if "m3" in cl: return (340, 1500, "Front", "RWD")
    if "m4" in cl: return (425, 1497, "Front", "RWD")
    if "z4" in cl: return (231, 1365, "Front", "RWD")
    if "911" in cl: return (350, 1350, "Rear", "RWD")
    if "cayman" in cl: return (385, 1340, "Mid", "RWD")
    if "golf" in cl: return (200, 1336, "Front", "FWD")
    if "megane" in cl: return (225, 1355, "Front", "FWD")
    if "clio" in cl: return (180, 1100, "Front", "FWD")
    if "190 e" in cl or "190e" in cl: return (235, 1340, "Front", "RWD")
    if "griffith" in cl: return (340, 1060, "Front", "RWD")
    if "alfa" in cl: return (200, 1300, "Front", "FWD")
    if "ferrari" in cl: return (500, 1350, "Mid", "RWD")
    if "lamborghini" in cl: return (550, 1450, "Mid", "AWD")
    if "aston" in cl: return (450, 1700, "Front", "RWD")
    if "audi" in cl: return (250, 1450, "Front", "AWD")
    
    # Generic fallback
    return (220, 1300, "Front", "RWD")

print("Specification matcher ready!")


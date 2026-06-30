"""
model_db.py — Line 6 HX / POD Go model-ID catalog.

Maps internal model identifiers (the @model field inside a preset's blocks)
to a (category, display_name, real_hardware) tuple.

POD Go runs the same HX modeling engine as the Helix family and shares these
model IDs, though POD Go exposes a SUBSET of the full Helix model list. Treat
this as a high-quality seed: the app also learns whatever models actually appear
in the presets you upload, so anything POD Go-specific is picked up at runtime.

Model-ID -> hardware mappings derived from the community-maintained
GhostNote17/HelixNativePresets project (MIT licensed) and the Line 6 Owner's
Manuals. Not affiliated with or endorsed by Line 6 / Yamaha Guitar Group.
"""

MODEL_DB = {
    # ===== Amp =====
    'HD2_AmpUSSmallTweed': ('Amp', 'US Small Tweed', 'Fender Champ'),
    'HD2_AmpUSDeluxeNrml': ('Amp', 'US Deluxe Nrml', 'Fender Deluxe Reverb (Normal)'),
    'HD2_AmpUSDeluxeNrm': ('Amp', 'US Deluxe Nrm', 'Fender Deluxe Reverb (Normal)'),
    'HD2_AmpUSDeluxeVib': ('Amp', 'US Deluxe Vib', 'Fender Deluxe Reverb (Vibrato)'),
    'HD2_AmpUSDoubleNrm': ('Amp', 'US Double Nrm', 'Fender Twin Reverb (Normal)'),
    'HD2_AmpUSDoubleNrml': ('Amp', 'US Double Nrm', 'Fender Twin Reverb (Normal)'),
    'HD2_AmpUSDoubleVib': ('Amp', 'US Double Vib', 'Fender Twin Reverb (Vibrato)'),
    'HD2_AmpUSPrincess': ('Amp', 'US Princess', 'Fender Princeton Reverb'),
    'HD2_AmpSoupPro': ('Amp', 'Soup Pro', 'Supro S6420'),
    'HD2_AmpStoneAge185': ('Amp', 'Stone Age 185', 'Gibson EH-185'),
    'HD2_AmpTweedBluesNrm': ('Amp', 'Tweed Blues Nrm', 'Fender Bassman (Normal)'),
    'HD2_AmpTweedBluesBrt': ('Amp', 'Tweed Blues Brt', 'Fender Bassman (Bright)'),
    'HD2_AmpMailOrderTwin': ('Amp', 'Mail Order Twin', 'Silvertone 1484'),
    'HD2_AmpVoltageQueen': ('Amp', 'Voltage Queen', 'Victoria Electro King'),
    'HD2_AmpTucknGo': ('Amp', 'Tuck & Go', 'Ampeg Jet J-20'),
    'HD2_AmpCaliIVR1': ('Amp', 'Cali IV Rhythm 1', 'MESA/Boogie Mk IV (R1)'),
    'HD2_AmpCaliIVRhythm1': ('Amp', 'Cali IV Rhythm 1', 'MESA/Boogie Mk IV (R1)'),
    'HD2_AmpCaliIVRhythm2': ('Amp', 'Cali IV Rhythm 2', 'MESA/Boogie Mk IV (R2)'),
    'HD2_AmpCaliIVLead': ('Amp', 'Cali IV Lead', 'MESA/Boogie Mk IV (Lead)'),
    'HD2_AmpCaliRectifire': ('Amp', 'Cali Rectifire', 'MESA/Boogie Dual Rectifier'),
    'HD2_AmpCaliTexasCh1': ('Amp', 'Cali Texas Ch1', 'MESA/Boogie Lonestar (Ch1)'),
    'HD2_AmpCaliTexasCh2': ('Amp', 'Cali Texas Ch2', 'MESA/Boogie Lonestar (Ch2)'),
    'HD2_AmpCaliBass': ('Amp', 'Cali Bass', 'MESA/Boogie Bass 400+'),
    'HD2_AmpCali400Ch1': ('Amp', 'Cali 400 Ch1', 'MESA/Boogie Bass 400 (Ch1)'),
    'HD2_AmpCali400Ch2': ('Amp', 'Cali 400 Ch2', 'MESA/Boogie Bass 400+ (Ch2)'),
    'HD2_AmpBritPlexi': ('Amp', 'Brit Plexi', 'Marshall Super Lead 100'),
    'HD2_AmpBritPlexiNrm': ('Amp', 'Brit Plexi Nrm', 'Marshall Super Lead 100 (Normal)'),
    'HD2_AmpBritPlexiBrt': ('Amp', 'Brit Plexi Brt', 'Marshall Super Lead 100 (Bright)'),
    'HD2_AmpBritPlexiJump': ('Amp', 'Brit Plexi Jump', 'Marshall Super Lead 100 (Jumped)'),
    'HD2_AmpBrit2204': ('Amp', 'Brit 2204', 'Marshall JCM800 2204'),
    'HD2_AmpBritJ45Nrm': ('Amp', 'Brit J-45 Nrm', 'Marshall JTM-45 (Normal)'),
    'HD2_AmpBritJ45Brt': ('Amp', 'Brit J-45 Brt', 'Marshall JTM-45 (Bright)'),
    'HD2_AmpBritTremBrt': ('Amp', 'Brit Trem Brt', 'Marshall JTM-50 (Bright)'),
    'HD2_AmpBritTremJump': ('Amp', 'Brit Trem Jump', 'Marshall JTM-50 (Jumped)'),
    'HD2_AmpBritP75Nrm': ('Amp', 'Brit P-75 Nrm', 'Park 75 (Normal)'),
    'HD2_AmpBritP75Brt': ('Amp', 'Brit P-75 Brt', 'Park 75 (Bright)'),
    'HD2_AmpEssexA15': ('Amp', 'Essex A-15', 'Vox AC-15'),
    'HD2_AmpEssexA30': ('Amp', 'Essex A-30', 'Vox AC-30 (Top Boost)'),
    'HD2_AmpA30FawnNrm': ('Amp', 'A30 Fawn Nrm', 'Vox AC-30 Fawn (Normal)'),
    'HD2_AmpA30FawnBrt': ('Amp', 'A30 Fawn Brt', 'Vox AC-30 Fawn (Bright)'),
    'HD2_AmpMatchstickCh1': ('Amp', 'Matchstick Ch1', 'Matchless DC-30 (Ch1)'),
    'HD2_AmpMatchstickCh2': ('Amp', 'Matchstick Ch2', 'Matchless DC-30 (Ch2)'),
    'HD2_AmpMatchstickJump': ('Amp', 'Matchstick Jump', 'Matchless DC-30 (Jumped)'),
    'HD2_AmpGermanMahadeva': ('Amp', 'German Mahadeva', 'Bogner Shiva'),
    'HD2_AmpGermanUbersonic': ('Amp', 'German Ubersonic', 'Bogner Überschall'),
    'HD2_AmpSoloLeadOD': ('Amp', 'Solo Lead OD', 'Soldano SLO-100 (Overdrive)'),
    'HD2_AmpSoloLeadClean': ('Amp', 'Solo Lead Clean', 'Soldano SLO-100 (Clean)'),
    'HD2_AmpSoloLeadCrunch': ('Amp', 'Solo Lead Crunch', 'Soldano SLO-100 (Crunch)'),
    'HD2_AmpANGLMeteor': ('Amp', 'ANGL Meteor', 'ENGL Fireball 100'),
    'HD2_AmpAnglMeteor': ('Amp', 'ANGL Meteor', 'ENGL Fireball 100'),
    'HD2_AmpDasBenzinMega': ('Amp', 'Das Benzin Mega', 'Diezel Herbert (Mega Ch)'),
    'HD2_AmpPVPanama': ('Amp', 'PV Panama', 'Peavey 5150'),
    'HD2_AmpPVVitriolLead': ('Amp', 'PV Vitriol Lead', 'Peavey 6505+ (Lead)'),
    'HD2_AmpRevvGenPurple': ('Amp', 'Revv Gen Purple', 'Revv Generator 120 (Purple)'),
    'HD2_AmpRevvGenRed': ('Amp', 'Revv Gen Red', 'Revv Generator 120 (Red)'),
    'HD2_AmpPlacaterClean': ('Amp', 'Placater Clean', 'Friedman BE-100 (Clean)'),
    'HD2_AmpPlacaterDirty': ('Amp', 'Placater Dirty', 'Friedman BE-100 (BE/HBE)'),
    'HD2_AmpDerailedIngrid': ('Amp', 'Derailed Ingrid', 'Trainwreck Express'),
    'HD2_AmpBusyOneCh1': ('Amp', 'Busy One Ch1', 'Diezel VH4 (Ch1)'),
    'HD2_AmpBusyOneCh2': ('Amp', 'Busy One Ch2', 'Diezel VH4 (Ch2)'),
    'HD2_AmpMandarin80': ('Amp', 'Mandarin 80', 'Orange OR80'),
    'HD2_AmpMandarinRocker': ('Amp', 'Mandarin Rocker', 'Orange Rockerverb'),
    'HD2_AmpWhoWatt100': ('Amp', 'WhoWatt 100', 'Hiwatt DR103'),
    'HD2_AmpCartographer': ('Amp', 'Cartographer', 'Ben Adrian Cartographer'),
    'HD2_AmpGrammaticoNrm': ('Amp', 'Grammatico Nrm', 'Grammatico LaGrange (Normal)'),
    'HD2_AmpGrammaticoJump': ('Amp', 'Grammatico Jump', 'Grammatico LaGrange (Jumped)'),
    'HD2_AmpGSG100': ('Amp', 'GSG 100', 'Grammatico GSG100'),
    'HD2_AmpInterstateZed': ('Amp', 'Interstate Zed', 'Dr. Z Route 66'),
    'HD2_AmpDividedDuo': ('Amp', 'Divided Duo', 'Divided by 13 9/15'),
    'HD2_AmpMoonJump': ('Amp', 'Moo)))n Jump', 'Moonlight Amplification'),
    'HD2_AmpArchetypeClean': ('Amp', 'Archetype Clean', 'Paul Reed Smith Archon (Clean)'),
    'HD2_AmpArchetypeLead': ('Amp', 'Archetype Lead', 'Paul Reed Smith Archon (Lead)'),
    'HD2_AmpJazzRivet120': ('Amp', 'Jazz Rivet 120', 'Roland JC-120'),
    'HD2_AmpCosmicGlue': ('Amp', 'Cosmic Glue', 'Supro S6616'),
    'HD2_AmpLine6Litigator': ('Amp', 'Litigator', 'Line 6 Original (Blackface-style)'),
    'HD2_AmpLine6Badonk': ('Amp', 'Badonk', 'Line 6 Original (High Gain)'),
    'HD2_AmpLine6Elektrik': ('Amp', 'Elektrik', 'Line 6 Original'),
    'HD2_AmpLine6Epicenter': ('Amp', 'Epicenter', 'Line 6 Original (Bass)'),
    'HD2_AmpLine6Epic': ('Amp', 'Line 6 Epic', 'Line 6 Original'),
    'HD2_AmpLine6Fatality': ('Amp', 'Line 6 Fatality', 'Line 6 Original (Fatality)'),
    'HD2_AmpLine6Elmsley': ('Amp', 'Elmsley', 'Line 6 Original'),
    'HD2_AmpLine6Ventoux': ('Amp', 'Ventoux', 'Line 6 Original'),
    'HD2_AmpLine62204Mod': ('Amp', 'Line 6 2204 Mod', 'Line 6 Modified JCM800'),
    'HD2_AmpSVT4Pro': ('Amp', 'SVT-4 Pro', 'Ampeg SVT-4 Pro'),
    'HD2_AmpSVTNrml': ('Amp', 'SVT Nrm', 'Ampeg SVT (Normal)'),
    'HD2_AmpSVTBright': ('Amp', 'SVT Bright', 'Ampeg SVT (Bright)'),
    'HD2_AmpSVBeastNrm': ('Amp', 'SV Beast Nrm', 'Ampeg SVT (Beast Mode)'),
    'HD2_AmpSVBeastBrt': ('Amp', 'SV Beast Brt', 'Ampeg SVT (Beast Mode, Bright)'),
    'HD2_AmpGCougar800': ('Amp', 'G Cougar 800', 'Gallien-Krueger 800RB'),
    'HD2_AmpAgua51': ('Amp', 'Agua 51', 'Aguilar DB 751'),
    'HD2_AmpAguaSledge': ('Amp', 'Agua Sledge', 'Aguilar Tone Hammer'),
    'HD2_AmpDelSol300': ('Amp', 'Del Sol 300', 'Sunn Coliseum 300'),
    'HD2_AmpWoodyBlue': ('Amp', 'Woody Blue', 'Acoustic 360'),
    # ===== Preamp =====
    'HD2_PreampUSDoubleNrm': ('Preamp', 'US Double Nrm Pre', 'Fender Twin Preamp'),
    'HD2_PreampUSDoubleVib': ('Preamp', 'US Double Vib Pre', 'Fender Twin Preamp (Vibrato)'),
    'HD2_PreampUSDeluxeNrm': ('Preamp', 'US Deluxe Nrm Pre', 'Fender Deluxe Reverb Preamp'),
    'HD2_PreampEssexA15': ('Preamp', 'Essex A-15 Pre', 'Vox AC-15 Preamp'),
    'HD2_PreampBusyOneCh2': ('Preamp', 'Busy One Ch2 Pre', 'Diezel VH4 Preamp (Ch2)'),
    'HD2_PreampSVT4Pro': ('Preamp', 'SVT-4 Pro Pre', 'Ampeg SVT-4 Pro Preamp'),
    'HD2_PreampVintagePre': ('Preamp', 'Vintage Pre', 'Generic Vintage Preamp'),
    'HD2_PreampCaliIVLead': ('Preamp', 'Cali IV Lead Pre', 'MESA/Boogie Mk IV Preamp'),
    'HD2_PreampBritPlexi': ('Preamp', 'Brit Plexi Pre', 'Marshall Plexi Preamp'),
    'HD2_PreampBrit2204': ('Preamp', 'Brit 2204 Pre', 'Marshall JCM800 Preamp'),
    # ===== Cab =====
    'HD2_Cab1x10PrincessCopperhead': ('Cab', '1x10 Princess', 'Fender Princeton'),
    'HD2_Cab1x12BlueBell': ('Cab', '1x12 Blue Bell', 'Vox w/ Blue Alnico'),
    'HD2_Cab1x12Celest12H': ('Cab', '1x12 Celest 12-H', 'Celestion G12H'),
    'HD2_Cab1x12DelSol': ('Cab', '1x12 Del Sol', 'Sunn cab'),
    'HD2_Cab1x12FieldCoil': ('Cab', '1x12 Field Coil', 'Field Coil speaker'),
    'HD2_Cab1x12Grammatico5E3': ('Cab', '1x12 Grammatico', 'Grammatico 5E3'),
    'HD2_Cab1x12Lead80': ('Cab', '1x12 Lead 80', 'Celestion Lead 80'),
    'HD2_Cab1x12MatchG25': ('Cab', '1x12 Match G25', 'Matchless w/ Greenback 25'),
    'HD2_Cab1x12MatchH30': ('Cab', '1x12 Match H30', 'Matchless w/ G12H30'),
    'HD2_Cab1x12PrincessBlue': ('Cab', '1x12 Princess Blue', 'Fender Princeton w/ Blue'),
    'HD2_Cab1x12USDeluxe': ('Cab', '1x12 US Deluxe', 'Fender Deluxe'),
    'HD2_Cab1x15TucknGo': ('Cab', '1x15 Tuck & Go', 'Ampeg Jet cab'),
    'HD2_Cab1x18DelSol': ('Cab', '1x18 Del Sol', 'Sunn 1x18'),
    'HD2_Cab1x18WoodyBlue': ('Cab', '1x18 Woody Blue', 'Acoustic 360 cab'),
    'HD2_Cab2x12BlueBell': ('Cab', '2x12 Blue Bell', 'Vox AC-30 w/ Blue Alnico'),
    'HD2_Cab2x12DoubleC12N': ('Cab', '2x12 Double C12N', 'Fender Twin C12N'),
    'HD2_Cab2x12Interstate': ('Cab', '2x12 Interstate', 'Dr. Z 2x12'),
    'HD2_Cab2x12JazzRivet': ('Cab', '2x12 Jazz Rivet', 'Roland JC-120 cab'),
    'HD2_Cab2x12MailC12Q': ('Cab', '2x12 Mail C12Q', 'Silvertone C12Q'),
    'HD2_Cab2x12SilverBell': ('Cab', '2x12 Silver Bell', 'Vox w/ Silver Bell'),
    'HD2_Cab4x10Rhino': ('Cab', '4x10 Rhino', 'Fender Super Reverb'),
    'HD2_Cab4x10TweedP10R': ('Cab', '4x10 Tweed P10R', 'Fender Bassman 4x10'),
    'HD2_Cab4x121960T75': ('Cab', '4x12 1960 T75', 'Marshall 1960 w/ T75'),
    'HD2_Cab4x12Blackback30': ('Cab', '4x12 Blackback 30', 'Marshall w/ Blackback'),
    'HD2_Cab4x12Greenback25': ('Cab', '4x12 Greenback 25', 'Marshall w/ Greenback 25W'),
    'HD2_Cab4X12CaliV30': ('Cab', '4x12 Cali V30', 'MESA/Boogie w/ V30'),
    'HD2_Cab4x12CaliV30': ('Cab', '4x12 Cali V30', 'MESA/Boogie w/ V30'),
    'HD2_Cab4x12UberT75': ('Cab', '4x12 Uber T75', 'Bogner w/ T75'),
    'HD2_Cab4x12UberV30': ('Cab', '4x12 Uber V30', 'Bogner w/ V30'),
    'HD2_Cab4x12WhoWatt100': ('Cab', '4x12 WhoWatt', 'Hiwatt w/ Fane'),
    'HD2_Cab4x12XXLV30': ('Cab', '4x12 XXL V30', 'Marshall 1960 w/ V30'),
    'HD2_Cab8x10SVBeast': ('Cab', '8x10 SV Beast', 'Ampeg SVT 8x10'),
    'HD2_Cab1x6x9SoupProEllipse': ('Cab', '1x6x9 Soup Pro', 'Supro S6420 Elliptical Speaker'),
    'HD2_Cab2x15Brute': ('Cab', '2x15 Brute', 'Sunn 2x15 w/ JBL D140'),
    'HD2_Cab4x12Greenback20': ('Cab', '4x12 Greenback 20', 'Marshall w/ Celestion G12M Greenback'),
    'HD2_Cab4x12MandarinEM': ('Cab', '4x12 Mandarin EM', 'Orange PPC412'),
    'HD2_Cab4x12SoloLeadEM': ('Cab', '4x12 Solo Lead EM', 'Soldano 4x12'),
    'HD2_CabMicIr_1x10USPrincessWithPan': ('Cab', '1x10 US Princess', 'Fender Princeton (dual mic)'),
    'HD2_CabMicIr_1x12CaliEXTWithPan': ('Cab', '1x12 Cali EXT', 'MESA/Boogie Extension (dual mic)'),
    'HD2_CabMicIr_1x12Epicenter': ('Cab', '1x12 Epicenter', 'Line 6 Epicenter cab'),
    'HD2_CabMicIr_1x12GrammaticoWithPan': ('Cab', '1x12 Grammatico', 'Grammatico (dual mic)'),
    'HD2_CabMicIr_1x12OpenCast': ('Cab', '1x12 Open Cast', 'Open-back 1x12'),
    'HD2_CabMicIr_1x12OpenCastWithPan': ('Cab', '1x12 Open Cast', 'Open-back 1x12 (dual mic)'),
    'HD2_CabMicIr_1x12USDeluxe': ('Cab', '1x12 US Deluxe', 'Fender Deluxe (mic)'),
    'HD2_CabMicIr_1x12USDeluxeWithPan': ('Cab', '1x12 US Deluxe', 'Fender Deluxe (dual mic)'),
    'HD2_CabMicIr_2x12BlueBellWithPan': ('Cab', '2x12 Blue Bell', 'Vox AC-30 Blue (dual mic)'),
    'HD2_CabMicIr_2x12DoubleC12N': ('Cab', '2x12 Double C12N', 'Fender Twin (mic)'),
    'HD2_CabMicIr_2x12DoubleC12NWithPan': ('Cab', '2x12 Double C12N', 'Fender Twin (dual mic)'),
    'HD2_CabMicIr_2x12JazzRivetWithPan': ('Cab', '2x12 Jazz Rivet', 'Roland JC-120 (dual mic)'),
    'HD2_CabMicIr_2x12MailC12QWithPan': ('Cab', '2x12 Mail C12Q', 'Silvertone (dual mic)'),
    'HD2_CabMicIr_2x12MandarinWithPan': ('Cab', '2x12 Mandarin', 'Orange (dual mic)'),
    'HD2_CabMicIr_2x12MatchG25WithPan': ('Cab', '2x12 Match G25', 'Matchless G25 (dual mic)'),
    'HD2_CabMicIr_2x12MatchH30WithPan': ('Cab', '2x12 Match H30', 'Matchless H30 (dual mic)'),
    'HD2_CabMicIr_2x12SilverBellWithPan': ('Cab', '2x12 Silver Bell', 'Vox Silver Bell (dual mic)'),
    'HD2_CabMicIr_2x15BruteWithPan': ('Cab', '2x15 Brute', 'Bass 2x15 (dual mic)'),
    'HD2_CabMicIr_4x10GardenWithPan': ('Cab', '4x10 Garden', 'Fender 4x10 (dual mic)'),
    'HD2_CabMicIr_4x10TweedP10RWithPan': ('Cab', '4x10 Tweed P10R', 'Fender Bassman (dual mic)'),
    'HD2_CabMicIr_4x12BlackbackH30WithPan': ('Cab', '4x12 Blackback H30', 'Marshall Blackback (dual mic)'),
    'HD2_CabMicIr_4x12CaliV30': ('Cab', '4x12 Cali V30', 'MESA/Boogie V30 (mic)'),
    'HD2_CabMicIr_4x12CaliV30WithPan': ('Cab', '4x12 Cali V30', 'MESA/Boogie V30 (dual mic)'),
    'HD2_CabMicIr_4x12Greenback25': ('Cab', '4x12 Greenback 25', 'Marshall Greenback (mic)'),
    'HD2_CabMicIr_4x12Greenback25WithPan': ('Cab', '4x12 Greenback 25', 'Marshall Greenback (dual mic)'),
    'HD2_CabMicIr_4x12MOONT75WithPan': ('Cab', '4x12 Moon T75', 'Moon 4x12 T75 (dual mic)'),
    'HD2_CabMicIr_4x12Mandarin': ('Cab', '4x12 Mandarin', 'Orange 4x12 (mic)'),
    'HD2_CabMicIr_4x12MandarinWithPan': ('Cab', '4x12 Mandarin', 'Orange 4x12 (dual mic)'),
    'HD2_CabMicIr_4x12UberT75WithPan': ('Cab', '4x12 Uber T75', 'Bogner T75 (dual mic)'),
    'HD2_CabMicIr_4x12UberV30WithPan': ('Cab', '4x12 Uber V30', 'Bogner V30 (dual mic)'),
    'HD2_CabMicIr_8x10SVTAV': ('Cab', '8x10 SVT AV', 'Ampeg SVT (mic)'),
    'HD2_CabMicIr_8x10SVTAVWithPan': ('Cab', '8x10 SVT AV', 'Ampeg SVT (dual mic)'),
    # ===== Drive =====
    'HD2_DistKinkyBoost': ('Drive', 'Kinky Boost', 'Xotic EP Booster'),
    'HD2_DistMinotaur': ('Drive', 'Minotaur', 'Klon Centaur'),
    'HD2_DistTeemah': ('Drive', 'Teemah!', 'Paul Cochrane Timmy'),
    'HD2_DistScream808': ('Drive', 'Scream 808', 'Ibanez TS808 Tube Screamer'),
    'HD2_DistHedgehogD9': ('Drive', 'Hedgehog D9', 'Maxon SD-9 Sonic Distortion'),
    'HD2_DistStuporOD': ('Drive', 'Stupor OD', 'Boss SD-1'),
    'HD2_DistDerangedMaster': ('Drive', 'Deranged Master', 'Dallas Rangemaster'),
    'HD2_DistTriangleFuzz': ('Drive', 'Triangle Fuzz', 'EHX Big Muff Pi (Triangle)'),
    'HD2_DistIndustrialFuzz': ('Drive', 'Industrial Fuzz', 'Z.Vex Fuzz Factory'),
    'HD2_DistBitcrusher': ('Drive', 'Bitcrusher', 'Line 6 Bitcrusher'),
    'HD2_DistHorizonDrive': ('Drive', 'Horizon Drive', 'Horizon Devices Precision Drive'),
    'HD2_DistDhyanaDrive': ('Drive', 'Dhyana Drive', 'Hermida Zendrive'),
    'HD2_DistCompulsiveDrive': ('Drive', 'Compulsive Drive', 'Fulltone OCD'),
    'HD2_DistValveDriver': ('Drive', 'Valve Driver', 'Chandler Tube Driver'),
    'HD2_DistTopSecretOD': ('Drive', 'Top Secret OD', 'DOD OD-250'),
    'HD2_DistDeezOneMod': ('Drive', 'Deez One Mod', 'Boss DS-1 (Keeley Mod)'),
    'HD2_DistMegaphone': ('Drive', 'Megaphone', 'Line 6 Megaphone'),
    'HD2_DistZeroAmpBassDI': ('Drive', 'Zero Amp Bass DI', 'Tech 21 SansAmp'),
    'HD2_DistHeirApparent': ('Drive', 'Heir Apparent', 'AnalogMan Prince of Tone'),
    'HD2_DistKWB': ('Drive', 'KWB', 'Benadrian KWB'),
    'HD2_DistToneSovereign': ('Drive', 'Tone Sovereign', 'Wampler Sovereign'),
    'HD2_DistTycoctaviaFuzz': ('Drive', 'Tycoctavia Fuzz', 'Tycobrahe Octavia'),
    'HD2_DistRamsHead': ('Drive', "Ram's Head", "EHX Big Muff Pi (Ram's Head)"),
    'HD2_DistObsidian7000': ('Drive', 'Obsidian 7000', 'Darkglass Microtubes B7K'),
    'HD2_DistClawthornDrive': ('Drive', 'Clawthorn Drive', 'EHX Crayon'),
    'HD2_DistArbitratorFuzz': ('Drive', 'Arbitrator Fuzz', 'Arbiter Fuzz Face'),
    'HD2_DistBallisticFuzz': ('Drive', 'Ballistic Fuzz', 'Balthazar Fuzz'),
    'HD2_DistPocketFuzz': ('Drive', 'Pocket Fuzz', 'Jordan Boss Tone'),
    'HD2_DistDeezOneVintage': ('Drive', 'Deez One Vintage', 'Boss DS-1'),
    'HD2_DistPillars': ('Drive', 'Pillars', 'Line 6 Pillars'),
    'HD2_DistVerminDist': ('Drive', 'Vermin Dist', 'Pro Co RAT'),
    'HD2_DistVitalDist': ('Drive', 'Vital Dist', 'MXR Dist+'),
    'HD2_DistThrifterFuzz': ('Drive', 'Thrifter Fuzz', 'Line 6 Thrifter'),
    'HD2_DistWringerFuzz': ('Drive', 'Wringer Fuzz', 'Garbage Wringer Fuzz'),
    'HD2_DistXenomorphFuzz': ('Drive', 'Xenomorph Fuzz', 'Industrial Fuzz variant'),
    'HD2_DistAmpegScramblerOD': ('Drive', 'Ampeg Scrambler', 'Ampeg Scrambler OD'),
    'HD2_DM4FacialFuzz': ('Drive', 'Facial Fuzz', 'Arbiter Fuzz Face (DM4)'),
    'HD2_DM4TubeDrive': ('Drive', 'Tube Drive', 'Chandler Tube Driver (DM4)'),
    # ===== Comp =====
    'HD2_CompressorDeluxeComp': ('Comp', 'Deluxe Comp', 'Line 6 Deluxe Compressor'),
    'HD2_CompressorRedSqueeze': ('Comp', 'Red Squeeze', 'MXR Dyna Comp'),
    'HD2_CompressorKinkyComp': ('Comp', 'Kinky Comp', 'Xotic SP Compressor'),
    'HD2_CompressorLAStudioComp': ('Comp', 'LA Studio Comp', 'Teletronix LA-2A'),
    'HD2_Compressor3BandComp': ('Comp', '3-Band Comp', 'Line 6 Multiband'),
    'HD2_CompressorRochesterComp': ('Comp', 'Rochester Comp', 'Ashly CLX-52'),
    'HD2_CompressorAutoSwell': ('Comp', 'Auto Swell', 'Line 6 Auto Swell'),
    # ===== Gate =====
    'HD2_GateNoiseGate': ('Gate', 'Noise Gate', 'Line 6 Noise Gate'),
    'HD2_GateHardGate': ('Gate', 'Hard Gate', 'Line 6 Hard Gate'),
    'HD2_GateHorizonGate': ('Gate', 'Horizon Gate', 'Horizon Devices Precision Gate'),
    # ===== EQ =====
    'HD2_EQParametric': ('EQ', 'Parametric EQ', 'Line 6 Parametric'),
    'HD2_EQGraphic10Band': ('EQ', '10-Band Graphic', 'MXR 10-Band EQ'),
    'HD2_EQLowCutHighCut': ('EQ', 'Low/High Cut', 'Simple Filter'),
    'HD2_EQSimple3Band': ('EQ', 'Simple EQ', '3-Band EQ'),
    'HD2_EQLowShelfHighShelf': ('EQ', 'Low/High Shelf', 'Shelf EQ'),
    'HD2_CaliQ': ('EQ', 'Cali Q', 'MESA/Boogie Graphic EQ'),
    # ===== Filter =====
    'HD2_FilterAutoFilter': ('Filter', 'Autofilter', 'Line 6 Autofilter'),
    'HD2_FilterMutantFilter': ('Filter', 'Mutant Filter', 'Musitronics Mu-Tron III'),
    'HD2_FM4VoiceBox': ('Filter', 'Voice Box', 'Line 6 FM4 Voice Box'),
    'HD2_FilterMysterFilter': ('Filter', 'Mystery Filter', 'Mu-Tron III'),
    'HD2_FilterAshevillePattrn': ('Filter', 'Asheville Pattrn', 'Line 6 Asheville Pattern'),
    # ===== Wah =====
    'HD2_WahTeardrop310': ('Wah', 'Teardrop 310', 'Dunlop Cry Baby'),
    'HD2_WahFassel': ('Wah', 'Fassel', 'Dunlop Cry Baby Original'),
    'HD2_WahChrome': ('Wah', 'Chrome', 'Vox V847'),
    'HD2_WahChromeCustom': ('Wah', 'Chrome Custom', 'Vox V847 Custom'),
    'HD2_WahWeeper': ('Wah', 'Weeper', 'Arbiter Cry Baby'),
    'HD2_WahConductor': ('Wah', 'Conductor', 'Maestro Boomerang'),
    'HD2_WahUKWah846': ('Wah', 'UK Wah 846', 'Vox V846'),
    'HD2_WahColorful': ('Wah', 'Colorful', 'Colorsound Wah'),
    'HD2_WahThroaty': ('Wah', 'Throaty', 'RMC Real McCoy'),
    # ===== Mod =====
    'HD2_TremoloTremolo': ('Mod', 'Tremolo', 'Line 6 Tremolo'),
    'HD2_TremoloPattern': ('Mod', 'Pattern Tremolo', 'Line 6 Pattern Tremolo'),
    'HD2_TremoloHarmonic': ('Mod', 'Harmonic Tremolo', 'Brownface-style'),
    'HD2_TremoloOpticalTrem': ('Mod', 'Optical Trem', 'Fender Optical Tremolo'),
    'HD2_Tremolo60sBiasTrem': ('Mod', '60s Bias Trem', 'Vox Bias Tremolo'),
    'HD2_VibratoBubbleVibrato': ('Mod', 'Bubble Vibrato', 'Boss VB-2'),
    'HD2_Chorus': ('Mod', 'Chorus', 'Line 6 Chorus'),
    'HD2_Chorus70sChorus': ('Mod', '70s Chorus', 'Boss CE-1'),
    'HD2_ChorusPlastiChorus': ('Mod', 'PlastiChorus', 'Arion SCH-Z'),
    'HD2_ChorusTrinityChorus': ('Mod', 'Trinity Chorus', 'Dytronics Tri-Stereo'),
    'HD2_FlangerGrayFlanger': ('Mod', 'Gray Flanger', 'MXR Flanger'),
    'HD2_FlangerHarmonicFlanger': ('Mod', 'Harmonic Flanger', 'A/DA Flanger'),
    'HD2_FlangerCourtesanFlange': ('Mod', 'Courtesan Flange', 'Electrix Flanger'),
    'HD2_PhaserScriptModPhase': ('Mod', 'Script Mod Phase', 'MXR Phase 90 (Script)'),
    'HD2_PhaserUbiquitousVibe': ('Mod', 'Ubiquitous Vibe', 'Shin-ei Uni-Vibe'),
    'HD2_RotaryRotary': ('Mod', 'Rotary', 'Leslie 145'),
    'HD2_Rotary145Rotary': ('Mod', '145 Rotary', 'Leslie 145 Rotary'),
    'HD2_Rotary122Rotary': ('Mod', '122 Rotary', 'Leslie 122 Rotary'),
    'HD2_RotaryVibeRotary': ('Mod', 'Vibe Rotary', 'Shin-ei Uni-Vibe'),
    'HD2_MM4AnalogFlanger': ('Mod', 'Analog Flanger', 'MXR Flanger (MM4)'),
    'HD2_MM4Dimension': ('Mod', 'Dimension', 'Roland Dimension D (MM4)'),
    'HD2_MM4UVibe': ('Mod', 'U-Vibe', 'Uni-Vibe (MM4)'),
    'HD2_RingModulatorAMRingMod': ('Mod', 'AM Ring Mod', 'Ring Modulator'),
    'HD2_RingModulatorPitchRingMod': ('Mod', 'Pitch Ring Mod', 'Pitch Ring Modulator'),
    'L6SPB_PolyChorus': ('Mod', 'Poly Chorus', 'Line 6 Poly Chorus'),
    # ===== Delay =====
    'HD2_DelaySimpleDelay': ('Delay', 'Simple Delay', 'Line 6 Simple Delay'),
    'HD2_DelayHarmonyDelay': ('Delay', 'Harmony Delay', 'Line 6 Harmony Delay'),
    'HD2_DelayMultitap4': ('Delay', 'Multitap 4', 'Line 6 Multitap 4'),
    'HD2_DelayMultitap6': ('Delay', 'Multitap 6', 'Line 6 Multitap 6'),
    'HD2_DelayModChorusEcho': ('Delay', 'Mod/Chorus Echo', 'Line 6 Mod Delay'),
    'HD2_DelaySweepEcho': ('Delay', 'Sweep Echo', 'Line 6 Sweep Echo'),
    'HD2_DelayDualDelay': ('Delay', 'Dual Delay', 'Line 6 Dual Delay'),
    'HD2_DelayMultiPass': ('Delay', 'Multipass', 'Line 6 Multipass'),
    'HD2_DelayBucketBrigade': ('Delay', 'Bucket Brigade', 'Boss DM-2'),
    'HD2_DelayVintageDigitalV2': ('Delay', 'Vintage Digital', 'Roland RE-style digital'),
    'HD2_DelayTransistorTape': ('Delay', 'Transistor Tape', 'Maestro EP-3'),
    'HD2_DelayAdriaticDelay': ('Delay', 'Adriatic Delay', 'Boss DM-2w style'),
    'HD2_DelayElephantMan': ('Delay', 'Elephant Man', 'EHX Deluxe Memory Man'),
    'HD2_DelayPingPong': ('Delay', 'Ping Pong', 'Line 6 Ping Pong'),
    'HD2_DelayReverseDelay': ('Delay', 'Reverse Delay', 'Line 6 Reverse'),
    'HD2_DelayDuckedDelay': ('Delay', 'Ducked Delay', 'TC Electronic-style'),
    'HD2_DelayDoubleDouble': ('Delay', 'Double Delay', 'Line 6 Double Delay'),
    'HD2_DelayCosmosEcho': ('Delay', 'Cosmos Echo', 'Roland RE-201 Space Echo'),
    'HD2_DelayPitch': ('Delay', 'Pitch Delay', 'Line 6 Pitch Delay'),
    'HD2_DelaySwellAdriatic': ('Delay', 'Swell Adriatic', 'Auto-swell delay'),
    'HD2_DL4LowResDelay': ('Delay', 'Low Res Delay', 'Line 6 DL4 Lo Res'),
    'HD2_DL4PingPong': ('Delay', 'DL4 Ping Pong', 'Line 6 DL4 Ping Pong'),
    'Victoria_ShufflingDelay': ('Delay', 'Shuffling Delay', 'Line 6 Shuffling Delay'),
    # ===== Reverb =====
    'HD2_ReverbHall': ('Reverb', 'Hall', 'Line 6 Hall'),
    'HD2_ReverbPlate': ('Reverb', 'Plate', 'Line 6 Plate'),
    'HD2_ReverbRoom': ('Reverb', 'Room', 'Line 6 Room'),
    'HD2_ReverbTile': ('Reverb', 'Tile', 'Line 6 Tile'),
    'HD2_ReverbChamber': ('Reverb', 'Chamber', 'Line 6 Chamber'),
    'HD2_ReverbSpring': ('Reverb', 'Spring', 'Line 6 Spring'),
    'HD2_ReverbHxSpring': ('Reverb', 'HX Spring', 'Line 6 HX Spring'),
    'HD2_ReverbEcho': ('Reverb', 'Echo', 'Line 6 Echo'),
    'HD2_ReverbCave': ('Reverb', 'Cave', 'Line 6 Cave'),
    'HD2_ReverbDucking': ('Reverb', 'Ducking', 'Line 6 Ducking'),
    'HD2_ReverbOcto': ('Reverb', 'Octo', 'Line 6 Octo'),
    'HD2_ReverbGlitz': ('Reverb', 'Glitz', 'Line 6 Glitz'),
    'HD2_ReverbGanymede': ('Reverb', 'Ganymede', 'Line 6 Ganymede'),
    'HD2_ReverbSearchlights': ('Reverb', 'Searchlights', 'Line 6 Searchlights'),
    'HD2_ReverbPlateaux': ('Reverb', 'Plateaux', 'Line 6 Plateaux'),
    'HD2_ReverbDoubleTank': ('Reverb', 'Double Tank', 'Line 6 Double Tank'),
    'HD2_Reverb63Spring': ('Reverb', "'63 Spring", "Fender '63 Spring"),
    'HD2_ReverbParticle': ('Reverb', 'Particle Verb', 'Line 6 Particle Verb'),
    'VIC_ReverbDynAmbience': ('Reverb', 'Dynamic Ambience', 'Line 6 Dynamic Ambience'),
    'VIC_ReverbDynRoom': ('Reverb', 'Dynamic Room', 'Line 6 Dynamic Room'),
    'VIC_ReverbRotating': ('Reverb', 'Rotating Reverb', 'Line 6 Rotating Reverb'),
    'VIC_DynPlate': ('Reverb', 'Dynamic Plate', 'Line 6 Dynamic Plate'),
    # ===== Pitch =====
    'HD2_PitchSimplePitch': ('Pitch', 'Simple Pitch', 'Line 6 Pitch Shifter'),
    'HD2_PitchTwinHarmony': ('Pitch', 'Twin Harmony', 'Line 6 Harmonizer'),
    'HD2_PitchPitchWham': ('Pitch', 'Pitch Wham', 'Digitech Whammy'),
    'HD2_PitchDualPitch': ('Pitch', 'Dual Pitch', 'Line 6 Dual Pitch'),
    'VIC_PitchTwelveString': ('Pitch', '12-String', 'Line 6 12-String Effect'),
    'HD2_DM4BassOctaver': ('Pitch', 'Bass Octaver', 'EBS OctaBass (DM4)'),
    'L6SPB_12String': ('Pitch', '12-String', 'Line 6 12-String Sim'),
    'L6SPB_PolyDowntune': ('Pitch', 'Poly Downtune', 'Line 6 Poly Downtune'),
    'L6SPB_PolyPitch': ('Pitch', 'Poly Pitch', 'Line 6 Poly Pitch'),
    'L6SPB_PolyWham': ('Pitch', 'Poly Wham', 'Line 6 Poly Whammy'),
    # ===== Synth =====
    'HD2_Synth3NoteGenerator': ('Synth', '3 Note Generator', 'Line 6 3-Note Synth'),
    'HD2_Synth4OSCGenerator': ('Synth', '4 OSC Generator', 'Line 6 4-OSC Synth'),
    'HD2_SynthSubtractive': ('Synth', 'Subtractive Synth', 'Line 6 Subtractive Synth'),
    'HD2_FM4SynthOMatic': ('Synth', 'Synth-O-Matic', 'Line 6 FM4 Synth-O-Matic'),
    'HD2_FM4Growler': ('Synth', 'Growler', 'Line 6 FM4 Growler'),
    'HD2_FM4SynthString': ('Synth', 'Synth String', 'Line 6 FM4 Synth String'),
    'HD2_FM4TronDown': ('Synth', 'Tron Down', 'Mu-Tron III Down'),
    'HD2_FM4TronUp': ('Synth', 'Tron Up', 'Mu-Tron III Up'),
    # ===== Utility =====
    'HD2_VolPanVol': ('Utility', 'Volume Pedal', 'Volume Pedal'),
    'HD2_VolPanGain': ('Utility', 'Gain Block', 'Gain/Mute Block'),
    'HD2_VolPanPan': ('Utility', 'Pan', 'Pan Block'),
    'HD2_VolPanStereoImager': ('Utility', 'Stereo Imager', 'Stereo Width'),
    'L6SPB_AcousGtrSim': ('Utility', 'Acoustic Sim', 'Line 6 Acoustic Guitar Sim'),
    'L6SPB_InfSustain': ('Utility', 'Infinite Sustain', 'Line 6 Infinite Sustain'),
    # ===== Routing =====
    'HD2_AppDSPFlow1Input': ('Routing', 'Input', 'DSP Input'),
    'HD2_AppDSPFlow2Input': ('Routing', 'Input B', 'DSP Input B'),
    'HD2_AppDSPFlowOutput': ('Routing', 'Output', 'DSP Output'),
    'HD2_AppDSPFlowSplitY': ('Routing', 'Split Y', 'Y Split'),
    'HD2_AppDSPFlowSplitAB': ('Routing', 'Split A/B', 'A/B Split'),
    'HD2_AppDSPFlowSplitDynamic': ('Routing', 'Split Dynamic', 'Dynamic Split'),
    'HD2_AppDSPFlowSplitCrossover': ('Routing', 'Split Crossover', 'Crossover Split'),
    'HD2_AppDSPFlowJoin': ('Routing', 'Join', 'Path Join'),

    # ===== POD Go verified — confirmed from real device exports =====
    # These use Mono/Stereo suffixes specific to POD Go firmware.
    # Do not replace with Helix catalog IDs — they will fail to import.
    'HD2_WahUKWah846Stereo':           ('Wah',     'UK Wah 846',       'Vox V846'),
    'HD2_WahTeardropStereo':           ('Wah',     'Teardrop',         'Dunlop Cry Baby'),
    'HD2_CompressorKinkyCompMono':     ('Comp',    'Kinky Comp',       'Cali76 Compact'),
    'HD2_CompressorROSSCompMono':      ('Comp',    'ROSS Comp',        'Ross Compressor'),
    'HD2_DistTeemahMono':              ('Drive',   'Teemah',           'Paul Cochrane Timmy'),
    'HD2_DistScream808Mono':           ('Drive',   'Scream 808',       'Ibanez TS808'),
    'HD2_DistKinkyBoostMono':          ('Drive',   'Kinky Boost',      'Xotic EP Booster'),
    'HD2_EQ_STATIC_ParametricStereo': ('EQ',      'Parametric EQ',    ''),
    'HD2_EQ_STATIC_GraphicStereo':    ('EQ',      'Graphic EQ',       ''),
    'HD2_ChorusStereo':                ('Mod',     'Chorus',           'Line 6 Chorus'),
    'HD2_FlangerStereo':               ('Mod',     'Flanger',          'Line 6 Flanger'),
    'HD2_PhaserStereo':                ('Mod',     'Phaser',           'Line 6 Phaser'),
    'HD2_TremoloTremoloStereo':        ('Mod',     'Tremolo',          'Line 6 Tremolo'),
    'HD2_DelaySimpleDelayStereo':      ('Delay',   'Simple Delay',     'Line 6 Simple Delay'),
    'HD2_DelayDigitalDelayStereo':     ('Delay',   'Digital Delay',    'Line 6 Digital Delay'),
    'HD2_ReverbGlitzStereo':           ('Reverb',  'Glitz',            'Line 6 Glitz'),
    'HD2_ReverbHallStereo':            ('Reverb',  'Hall',             'Line 6 Hall'),
    'HD2_ReverbPlateStereo':           ('Reverb',  'Plate',            'Line 6 Plate'),
    'HD2_ReverbRoomStereo':            ('Reverb',  'Room',             'Line 6 Room'),
    'HD2_ReverbSpringMono':            ('Reverb',  'Spring',           'Line 6 Spring'),
    'HD2_ImpulseResponse1024Mono':     ('Cab',     'Impulse Response', ''),
    'HD2_VolPanVolStereo':             ('Utility', 'Volume/Pan',       ''),
    'HD2_FXLoopMono1':                 ('Utility', 'Mono FX Loop',     ''),
}

# IDs confirmed to import without "unrecognized models" on a real POD Go.
# compact_catalog() only shows these so the LLM never picks an untested ID.
# Add more here after verifying them via build_catalog.py on your own exports.
PODGO_VERIFIED = frozenset({
    'HD2_WahUKWah846Stereo',
    'HD2_WahTeardropStereo',
    'HD2_CompressorKinkyCompMono',
    'HD2_CompressorROSSCompMono',
    'HD2_DistTeemahMono',
    'HD2_DistScream808Mono',
    'HD2_DistKinkyBoostMono',
    'HD2_EQ_STATIC_ParametricStereo',
    'HD2_EQ_STATIC_GraphicStereo',
    'HD2_ChorusStereo',
    'HD2_FlangerStereo',
    'HD2_PhaserStereo',
    'HD2_TremoloTremoloStereo',
    'HD2_DelaySimpleDelayStereo',
    'HD2_DelayDigitalDelayStereo',
    'HD2_ReverbGlitzStereo',
    'HD2_ReverbHallStereo',
    'HD2_ReverbPlateStereo',
    'HD2_ReverbRoomStereo',
    'HD2_ReverbSpringMono',
    'HD2_ImpulseResponse1024Mono',
    # Amps confirmed via DH CHORUS CLOUD and template testing
    'HD2_AmpA30FawnNrm',
    'HD2_AmpUSDoubleNrm',
    # Cabs confirmed via template testing
    'HD2_Cab2x12DoubleC12N',
})


# ─── Helper lookups ───────────────────────────────────────────────
import re

_BY_CATEGORY = {}
_BY_NAME = {}
for _mid, (_cat, _name, _real) in MODEL_DB.items():
    _BY_CATEGORY.setdefault(_cat, []).append(_mid)
    _BY_NAME[_name.lower()] = _mid

CATEGORIES = sorted(_BY_CATEGORY.keys())


def lookup(model_id):
    """Return (category, display_name, real_hardware) for a model id.
    Unknown ids are categorised by prefix so POD Go-only models still render."""
    if model_id in MODEL_DB:
        return MODEL_DB[model_id]
    prefix_map = {
        "Amp": "Amp", "Preamp": "Preamp", "Cab": "Cab", "Dist": "Drive",
        "Delay": "Delay", "Reverb": "Reverb", "Compressor": "Comp",
        "Comp": "Comp", "EQ": "EQ", "Filter": "Filter", "Wah": "Wah",
        "Pitch": "Pitch", "Synth": "Synth", "Gate": "Gate", "Chorus": "Mod",
        "Mod": "Mod", "Tremolo": "Mod", "Vibrato": "Mod", "Flanger": "Mod",
        "Phaser": "Mod", "Rotary": "Mod", "VolPan": "Utility", "FXLoop": "Utility",
    }
    m = re.match(r"(?:HD2_|VIC_|L6SPB_|HDV_)?([A-Za-z]+)", model_id or "")
    cat = "Unknown"
    if m:
        token = m.group(1)
        for key, val in prefix_map.items():
            if token.startswith(key):
                cat = val
                break
    return (cat, model_id, "")


def models_in_category(category):
    return list(_BY_CATEGORY.get(category, []))


def _tokens(s):
    return [t for t in re.split(r"[^a-z0-9]+", (s or "").lower()) if len(t) >= 3]


def find_model(query):
    """Match a human phrase to a model id by scoring name + real-hardware
    token overlap. Returns the best id or None. Avoids short-substring traps
    (e.g. 'marshall' must not match the 'Hall' reverb)."""
    q = (query or "").lower().strip()
    if not q:
        return None
    if q in _BY_NAME:
        return _BY_NAME[q]
    qtokens = set(_tokens(q))
    if not qtokens:
        return None
    # Category-implied words steer the match toward the right block type.
    cat_words = {
        "reverb": "Reverb", "verb": "Reverb",
        "delay": "Delay", "echo": "Delay",
        "fuzz": "Drive", "overdrive": "Drive", "distortion": "Drive",
        "drive": "Drive", "boost": "Drive",
        "compressor": "Comp", "comp": "Comp",
        "chorus": "Mod", "flanger": "Mod", "phaser": "Mod", "phase": "Mod",
        "tremolo": "Mod", "trem": "Mod", "vibrato": "Mod", "rotary": "Mod",
        "amp": "Amp", "preamp": "Preamp", "cab": "Cab", "cabinet": "Cab",
        "wah": "Wah", "synth": "Synth", "pitch": "Pitch", "octave": "Pitch",
        "gate": "Gate",
    }
    implied = {cat_words[t] for t in qtokens if t in cat_words}
    best, best_score = None, 0
    for mid, (cat, name, real) in MODEL_DB.items():
        cand = set(_tokens(name)) | set(_tokens(real))
        if not cand:
            continue
        overlap = qtokens & cand
        if not overlap:
            continue
        score = sum(len(t) for t in overlap)
        if qtokens <= cand:
            score += 5
        if implied and cat in implied:
            score += 12          # strong nudge toward the implied block type
        elif implied and cat not in implied:
            score -= 6           # penalise wrong-category coincidental hits
        if score > best_score:
            best, best_score = mid, score
    return best


def compact_catalog(categories=None):
    """Token-efficient listing for prompting the LLM, grouped by category.
    Only includes PODGO_VERIFIED ids so the LLM never proposes an untested model."""
    cats = categories or CATEGORIES
    out = []
    for cat in cats:
        ids = [mid for mid in _BY_CATEGORY.get(cat, []) if mid in PODGO_VERIFIED]
        if not ids:
            continue
        out.append(f"## {cat}")
        for mid in ids:
            _c, name, real = MODEL_DB[mid]
            tail = f"  ({real})" if real else ""
            out.append(f"{mid}  |  {name}{tail}")
    return "\n".join(out)

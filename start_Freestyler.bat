@echo off

cd /d "C:\Users\Administrator\Desktop\FreeStyler-VI-Pandemic\Lib"
start "" cmd /k "python final.py"
start "" cmd /k "python shoots.py"
@REM start "" cmd /k "python main.py"

@REM cd /d "C:\Users\Administrator\Desktop\FreeStyler-VI-Pandemic\Lib\trail_sl"
@REM start "" cmd /k "python trail.py"

cd /d "C:\Users\Administrator\Desktop\FreeStyler-VI-Pandemic\Lib\mtf_analysis"
@REM start "" cmd /k "python ranging_market.py"
start "" cmd /k "python fusion_acc.py"

cd /d "C:\Users\Administrator\Desktop\FreeStyler-VI-Pandemic\Lib\choppy_market"
start "" cmd /k "python choppy_market.py"

cd /d "C:\Users\Administrator\Desktop\FreeStyler-VI-Pandemic\Lib\random_trade"
start "" cmd /k "python random_trade.py"
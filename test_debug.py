
import wdb
wdb.set_trace()

for a in range(10):
    print(f"Iteración {a}")
    if a == 5:
        print("Punto de interrupción alcanzado")
        wdb.set_trace()  # Aquí se detendrá el depurador
        
print("Termina el programa test_debug.py")

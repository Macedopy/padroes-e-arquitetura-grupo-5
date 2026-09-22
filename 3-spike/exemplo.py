import threading
import time

class EstadoLeitos:

    def __init__(self, leitos):
        self._estado = {leito: {"reservado": False, "paciente": None, "unidade": None}
                         for leito in leitos}

    def snapshot(self, leito_id):
        return dict(self._estado[leito_id])

    def leito_livre(self, leito_id):
        return not self._estado[leito_id]["reservado"]

    def escrever_reserva(self, leito_id, paciente_id, unidade):
        self._estado[leito_id]["reservado"] = True
        self._estado[leito_id]["paciente"] = paciente_id
        self._estado[leito_id]["unidade"] = unidade

class DistributedLockManager:

    def __init__(self):
        self._locks = {}
        self._guarda = threading.Lock()

    def adquirir(self, leito_id, dono):
        with self._guarda:
            if leito_id in self._locks:
                return False
            self._locks[leito_id] = dono
            return True

    def liberar(self, leito_id, dono):
        with self._guarda:
            if self._locks.get(leito_id) == dono:
                del self._locks[leito_id]

class SistemaLegadoLeitos:

    def __init__(self, padrao_de_falhas):
        self._falhas_restantes = dict(padrao_de_falhas)

    def confirmar_reserva(self, leito_id, paciente_id):
        restantes = self._falhas_restantes.get(leito_id, 0)
        if restantes > 0:
            self._falhas_restantes[leito_id] = restantes - 1
            raise ConnectionError(f"legado indisponivel para {leito_id} "
                                   f"(tentativas restantes de falha: {restantes})")
        return True

def tentar_reservar_sem_lock(estado, leito_id, paciente_id, unidade, barreira, resultados):
    barreira.wait()
    if estado.leito_livre(leito_id):
        time.sleep(0.05)
        estado.escrever_reserva(leito_id, paciente_id, unidade)
        resultados[unidade] = "CONFIRMADA"
    else:
        resultados[unidade] = "RECUSADA (leito ja ocupado)"

def cenario_a_sem_lock():
    estado = EstadoLeitos(["LEITO-101"])
    resultados = {}
    barreira = threading.Barrier(2)

    t1 = threading.Thread(target=tentar_reservar_sem_lock,
                           args=(estado, "LEITO-101", "PACIENTE-01", "UPA-Sul",
                                 barreira, resultados))
    t2 = threading.Thread(target=tentar_reservar_sem_lock,
                           args=(estado, "LEITO-101", "PACIENTE-02", "Hospital-Central",
                                 barreira, resultados))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    confirmadas = sum(1 for v in resultados.values() if v == "CONFIRMADA")
    return resultados, confirmadas

def tentar_reservar_com_lock(estado, lock_mgr, leito_id, paciente_id, unidade,
                              barreira, resultados, atraso_antes_do_lock=0.0):
    barreira.wait()
    if atraso_antes_do_lock:
        time.sleep(atraso_antes_do_lock)
    if lock_mgr.adquirir(leito_id, unidade):
        time.sleep(0.05)
        estado.escrever_reserva(leito_id, paciente_id, unidade)
        resultados[unidade] = "CONFIRMADA"
        lock_mgr.liberar(leito_id, unidade)
    else:
        resultados[unidade] = "RECUSADA (lock ja adquirido por outra unidade)"

def cenario_b_com_lock():
    estado = EstadoLeitos(["LEITO-101"])
    lock_mgr = DistributedLockManager()
    resultados = {}
    barreira = threading.Barrier(2)

    t1 = threading.Thread(target=tentar_reservar_com_lock,
                           args=(estado, lock_mgr, "LEITO-101", "PACIENTE-01",
                                 "UPA-Sul", barreira, resultados, 0.0))
    t2 = threading.Thread(target=tentar_reservar_com_lock,
                           args=(estado, lock_mgr, "LEITO-101", "PACIENTE-02",
                                 "Hospital-Central", barreira, resultados, 0.02))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    confirmadas = sum(1 for v in resultados.values() if v == "CONFIRMADA")
    return resultados, confirmadas

def cenario_c_outbox():
    legado = SistemaLegadoLeitos(padrao_de_falhas={"LEITO-205": 2})
    outbox = [{"leito_id": "LEITO-205", "paciente_id": "PACIENTE-09",
               "sincronizado": False, "tentativas": 0}]

    log = []
    MAX_TENTATIVAS = 5
    for registro in outbox:
        while not registro["sincronizado"] and registro["tentativas"] < MAX_TENTATIVAS:
            registro["tentativas"] += 1
            try:
                legado.confirmar_reserva(registro["leito_id"], registro["paciente_id"])
                registro["sincronizado"] = True
                log.append(f"tentativa {registro['tentativas']}: sucesso")
            except ConnectionError as erro:
                log.append(f"tentativa {registro['tentativas']}: falhou ({erro})")

    return outbox[0], log

def main():
    print("=" * 72)
    print("SPIKE — ADR-003: Lock Distribuido + ACL + Outbox Transacional")
    print("Caso Saude / Envelope C — Grupo 05")
    print("=" * 72)

    print("\n[Cenario A] Duas unidades disputam o LEITO-101 SEM lock distribuido")
    resultados_a, confirmadas_a = cenario_a_sem_lock()
    for unidade in ("UPA-Sul", "Hospital-Central"):
        print(f"  - {unidade}: {resultados_a[unidade]}")
    print(f"  Reservas confirmadas para o mesmo leito: {confirmadas_a}")
    if confirmadas_a > 1:
        print("  RESULTADO: OVERBOOKING CONFIRMADO (defeito que o ADR-003 corrige)")
    else:
        print("  RESULTADO: sem overbooking neste cenario")

    print("\n[Cenario B] Mesma disputa, agora COM DistributedLockManager (Redlock)")
    resultados_b, confirmadas_b = cenario_b_com_lock()
    for unidade in ("UPA-Sul", "Hospital-Central"):
        print(f"  - {unidade}: {resultados_b[unidade]}")
    print(f"  Reservas confirmadas para o mesmo leito: {confirmadas_b}")
    if confirmadas_b == 1:
        print("  RESULTADO: OVERBOOKING EVITADO — apenas uma unidade reservou o leito")
    else:
        print("  RESULTADO: FALHA — o lock nao impediu o overbooking")

    print("\n[Cenario C] TransactionalOutboxHandler sincronizando com legado instavel")
    registro, log = cenario_c_outbox()
    for linha in log:
        print(f"  - {linha}")
    print(f"  Estado final do registro de Outbox: {registro}")
    if registro["sincronizado"]:
        print("  RESULTADO: reserva local preservada e sincronizada apos retentativas")
    else:
        print("  RESULTADO: reserva NAO sincronizada apos o limite de tentativas")

    print("\n" + "=" * 72)
    print("RESUMO")
    print("=" * 72)
    print(f"Cenario A (sem lock)  -> reservas confirmadas no mesmo leito: {confirmadas_a}"
          f" {'(OVERBOOKING)' if confirmadas_a > 1 else ''}")
    print(f"Cenario B (com lock)  -> reservas confirmadas no mesmo leito: {confirmadas_b}"
          f" {'(OK — sem overbooking)' if confirmadas_b == 1 else '(FALHA)'}")
    print(f"Cenario C (outbox)    -> sincronizado apos {registro['tentativas']} tentativa(s):"
          f" {registro['sincronizado']}")

if __name__ == "__main__":
    main()

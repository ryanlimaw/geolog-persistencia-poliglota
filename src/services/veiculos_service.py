import psycopg2 as pg
from db.clients import descartar_conexao_postgres, obter_banco_postgres

SQL_FROTA = """
    SELECT
        v.id     AS veiculo_id,
        v.placa,
        v.modelo,
        m.id     AS motorista_id,
        m.nome   AS motorista,
        m.status AS status_motorista
    FROM veiculos v
    INNER JOIN motoristas m ON m.id = v.motorista_id
    ORDER BY v.id;
"""

SQL_MOTORISTAS_POR_STATUS = """
    SELECT
        status,
        COUNT(*) AS quantidade
    FROM motoristas
    GROUP BY status
    ORDER BY quantidade DESC, status;
"""

class VeiculoService:
    def _consultar(self, sql: str, parametros: tuple = (), tentativa: int = 1) -> list[dict]:
        conexao = obter_banco_postgres()
        try:
            with conexao.cursor() as cursor:
                cursor.execute(sql, parametros)
                colunas = [coluna.name for coluna in cursor.description]
                return [dict(zip(colunas, linha)) for linha in cursor.fetchall()]
            
        except (pg.OperationalError, pg.InterfaceError):
            descartar_conexao_postgres(conexao)
            if tentativa == 1:
                return self._consultar(sql, parametros, tentativa=2)
            raise

        except pg.Error:
            if not conexao.autocommit and not conexao.closed:
                conexao.rollback()
            raise

    def get_veiculo_by_id(self, veiculo_id: int) -> dict:
        resultado = self._consultar(
            """
            SELECT
                v.placa,
                v.modelo,
                m.status,
                m.nome as motorista
            FROM veiculos v
            INNER JOIN motoristas m ON v.motorista_id = m.id
            WHERE v.id =  %s;
            """,
            (veiculo_id,),
        )

        return resultado[0] if resultado else {}

    def listar_frota(self) -> list[dict]:
        return self._consultar(SQL_FROTA)

    def contar_motoristas_por_status(self) -> list[dict]:
        return self._consultar(SQL_MOTORISTAS_POR_STATUS)

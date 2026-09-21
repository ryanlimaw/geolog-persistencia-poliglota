
from src.db.clients import obter_banco_postgres

class VeiculoService:
    def __init__(self):
        self.banco = obter_banco_postgres()

    def get_veiculo_by_id(self, veiculo_id: int) -> dict:
        with self.banco.cursor() as cursor:
            cursor.execute(
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

            resultado = cursor.fetchone()
            if resultado is None:
                return {}

            colunas = [coluna.name for coluna in cursor.description]
            return dict(zip(colunas, resultado))
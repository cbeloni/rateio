from pydantic import BaseModel

class PixRequest(BaseModel):
    name_receiver: str
    city_receiver: str
    key: str
    identification: str
    zipcode_receiver: str
    description: str
    amount: float

# Example usage
pix = PixRequest(
    name_receiver='Cauê Beloni',
    city_receiver='Santo André',
    key='cbeloni@gmail.com',
    identification='12345',
    zipcode_receiver='09291250',
    description='rateio mensal',
    amount=1.0
)
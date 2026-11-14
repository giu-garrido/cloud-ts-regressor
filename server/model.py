import numpy as np 
import pandas as pd
from numpy import concatenate
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


def load_data(file_path):
    """
    Le o arquivo CSV e retorna um DataFrame do pandas.
    """
    try:
        df = pd.read_csv(file_path)
        return df
    except Exception as e:
        print(e)
        return None

def prepare_data(df, target_column):
    """
    Prepara os dados para o treinamento do modelo.
    Separa as features e o target, normaliza os dados e divide em treino e teste.
    """
    try:
        X = df.drop(columns=[target_column])
        X = np.array(X, dtype=float)       
        y = df[target_column]
        y = np.array(y, dtype=float)

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        X_train, X_val, y_train, y_val = train_test_split(X_train, y_train, test_size=0.2, random_state=42)

        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_test = scaler.transform(X_test)
        X_val = scaler.transform(X_val)

        return X_train, X_test, y_train, y_test, X_val, y_val
    
    except Exception as e:
        print(e)
        return None, None, None, None, None, None



class Regressor:
    '''
    Implementação de um regressor linear simples.
    Os dados de entrada devem ser fornecidos já normalizados.

    '''

    def __init__(self):
        self.weights = None
        self.bias = None
        self.learning_coefficient = None
        self.max_iterations = 100

    def clear_model(self):
        self.weights = None
        self.bias = None
        self.learning_coefficient = None

    def score(self, X, y, weights=None, bias=None):
        """
        Calcula o R² do modelo.
        """

        if weights is None:
            weights = self.weights
        if bias is None:
            bias = self.bias
        
        y_pred = self.predict(X, weights, bias)

        sse = np.sum((y - y_pred) ** 2)
        sst = np.sum((y - np.mean(y)) ** 2) 

        if sst == 0:
            print("A variância do target é zero. O R² não pode ser calculado.")
            return 0.0
        
        r2_score =  1 -(sse / sst)
        
        return r2_score

    def _train(self, X_train, y_train, iterations,  X_val=None, y_val=None, learning_coefficient=None,validate=False):
        """
        Loop de treino do modelo. Percorre as amostrar e atualiza os pesos e o bias com base no erro.
        
        Se validate=True, divide os dados em treino e validação, e retorna o R² do modelo com base nos dados de validação.
        É usadpo para encontrar o melhor coeficiente de aprendizado.
        """
        
        train_weights = np.zeros(X_train.shape[1], dtype=float)
        train_bias = 0

        for loops in range(iterations):      
            for j in range(len(X_train)):
                y_pred = (X_train[j] @ train_weights) + train_bias

                train_weights += learning_coefficient * 2 * (y_train[j] - y_pred) * X_train[j]
                train_bias += learning_coefficient * 2 * (y_train[j] - y_pred)

        if validate:
            r2 = self.score(X_val, y_val, train_weights, train_bias)
        else:
            r2 = None

        return r2, train_weights, train_bias, learning_coefficient

    def fit(self, X_train, y_train, X_val, y_val, iterations=None):
        """
        Treina o modelo com a base de treino.

        Erro -> erro quadrático = (y - y_pred)²

        Faz uma busca por diferentes coeficientes de aprendizado e seleciona o melhor modelo com base no R².
        Depois treina o modelo com o melhor coeficiente de aprendizado.
        """

        test_learning_coefficients = [0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05]

        models = []

        if iterations is None:
            iterations = self.max_iterations

        for i in test_learning_coefficients: 
            r2, _, _, learning_coefficient = self._train(X_train, y_train, iterations=iterations, X_val=X_val, y_val=y_val, learning_coefficient=i, validate=True)
            models.append([r2, learning_coefficient])

        best_model = max(models, key=lambda x: x[0])
        learning_coefficient = best_model[1]

        X_final_train = concatenate((X_train, X_val), axis=0)
        y_final_train = concatenate((y_train, y_val), axis=0)

        _, weights, bias, _ = self._train(X_final_train, y_final_train, iterations=iterations, learning_coefficient=learning_coefficient, validate=False)
        self.weights = weights
        self.bias = bias
        self.learning_coefficient = learning_coefficient

        print(f"Modelo treinado com coeficiente de aprendizado = {learning_coefficient:.4f}")

        return None
        
    def predict(self, X, weights=None, bias=None):
        """
        Faz a previsão com base nos dados de entrada.
        """
        if weights is None:
            weights = self.weights
        if bias is None:
            bias = self.bias

        y_pred = X @ weights + bias
        return y_pred



if __name__ == "__main__":
    print("Teste model.py")

    df = load_data("C:\\Users\\thomd\\OneDrive\\Puc\\Aprendisado Supervisionado\\Trabalho final\\cloud-ts-regressor\\server\\PI_test-1.csv")
    X_train, X_test, y_train, y_test, X_val, y_val = prepare_data(df, target_column="time")

    print("Dados carregados e preparados com sucesso")

    print("Iniciando o treinamento do modelo")

    model = Regressor()
    model.fit(X_train, y_train, X_val, y_val)
    r2 = model.score(X_test, y_test)
    print(f"R² do modelo: {r2:.4f}")

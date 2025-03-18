import pandas as pd

# Загрузка данных из CSV файла
# Путь к вашему файлу, замените на актуальный путь к файлу
file_path = 'Water_with_laser_2.csv'

# Читаем CSV файл в DataFrame
df = pd.read_csv(file_path)

# Проверяем, что данные загружены корректно
print("Первыe 5 строк данных:")
print(df.head())

# Вычисляем среднее значение для каждого столбца
average_values = df.mean()

print("\nСреднее значение для N и Counts:")
print(average_values)

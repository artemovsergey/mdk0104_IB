# Эталонное решение практической работы 2

Вариант 1 «Калькулятор оценок». Решение служит образцом для проверки:
показывает структуру проекта, обработку неверного ввода, граничные случаи
и автоматические тесты.

## Структура

```text
practice-02/
├── ConditionalPractice.slnx
├── src/
│   └── ConditionalPractice/
│       ├── ConditionalPractice.csproj
│       ├── GradeCalculator.cs
│       ├── ScoreInput.cs
│       └── Program.cs
└── tests/
    └── ConditionalPractice.Tests/
        ├── ConditionalPractice.Tests.csproj
        ├── GradeCalculatorTests.cs
        └── ScoreInputTests.cs
```

- `GradeCalculator` — чистая функция `GetGrade(score)`; вне диапазона 0–100
  выбрасывает `ArgumentOutOfRangeException`.
- `ScoreInput` — разбор строки: `int.TryParse` плюс проверка диапазона.
- `Program` — консольный цикл: повторяет запрос при ошибке, выводит результат
  и завершается после корректного ввода.

## Запуск

```bash
dotnet run --project solutions/practice-02/src/ConditionalPractice
```

## Тесты

```bash
dotnet test solutions/practice-02/ConditionalPractice.slnx
```

Проверяются границы всех диапазонов (100, 90, 89, 80, 79, 70, 69, 60, 59, 0),
значения вне диапазона и разбор ввода: пустая строка, `null`, текст,
дробное число, отрицательное число, число больше 100.

## Что взять в студенческую работу

- отдельный класс с логикой, а не всё в `Program.cs`;
- проверка ввода до вычислений;
- тесты на границы, а не только на типичное значение;
- сообщения об ошибках на русском и понятный формат вывода.

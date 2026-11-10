# Практика 2 — эталон примера

Этот каталог — образец решения **примера** из практической работы 2
(«Проверка надёжности пароля»). Он не относится ни к одному из 15 вариантов:
варианты студенты выполняют самостоятельно.

## Что показывает эталон

- Разделение логики и ввода-вывода: правила проверки — в `PasswordValidator`,
  консольный цикл — в `Program.cs`.
- Повторный запрос при неверном вводе и команда `exit`.
- Граничные случаи: пустая строка, отсутствие цифры, заглавной буквы или
  спецсимвола.
- Модульные тесты xUnit на каждое правило и на их комбинацию.

## Структура

```
solutions/practice-02/
├── ConditionalPractice.slnx
├── README.md
├── src/ConditionalPractice/
│   ├── ConditionalPractice.csproj
│   ├── Program.cs
│   └── PasswordValidator.cs
└── tests/ConditionalPractice.Tests/
    ├── ConditionalPractice.Tests.csproj
    └── PasswordValidatorTests.cs
```

## Запуск

```bash
dotnet run --project solutions/practice-02/src/ConditionalPractice
```

## Тесты

```bash
dotnet test solutions/practice-02/ConditionalPractice.slnx
```

Тесты проверяют длину пароля, наличие цифры, заглавной буквы, каждого
спецсимвола из `!@#$%^&*`, а также итоговое правило `IsStrong`.

## Что взять в студенческую работу

- Такую же структуру: отдельный класс с правилами и тонкий `Program.cs`.
- Свой набор тестов на границы: 7 и 8 символов, пароль без каждой из четырёх
  групп символов, пустая строка.
- Свои скриншоты и README, как требует задание.

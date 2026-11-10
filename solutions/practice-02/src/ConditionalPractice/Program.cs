using ConditionalPractice;

// Повторяем запрос, пока не получим корректный балл.
while (true)
{
    Console.Write("Введите балл от 0 до 100: ");
    string? input = Console.ReadLine();

    if (!ScoreInput.TryParse(input, out int score))
    {
        Console.WriteLine("Ошибка: нужно целое число от 0 до 100.");
        continue;
    }

    Console.WriteLine($"Балл: {score}, оценка: {GradeCalculator.GetGrade(score)}");
    break;
}

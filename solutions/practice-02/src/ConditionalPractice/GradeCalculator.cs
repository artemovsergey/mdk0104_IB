namespace ConditionalPractice;

/// <summary>Переводит балл в буквенную оценку по шкале работы.</summary>
public static class GradeCalculator
{
    public static string GetGrade(int score)
    {
        if (score is < 0 or > 100)
        {
            throw new ArgumentOutOfRangeException(
                nameof(score), score, "Балл должен быть от 0 до 100.");
        }

        if (score >= 90)
        {
            return "A";
        }

        if (score >= 80)
        {
            return "B";
        }

        if (score >= 70)
        {
            return "C";
        }

        if (score >= 60)
        {
            return "D";
        }

        return "F";
    }
}

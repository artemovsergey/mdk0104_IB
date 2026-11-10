namespace ConditionalPractice;

/// <summary>Проверяет, что ввод — целое число от 0 до 100.</summary>
public static class ScoreInput
{
    public static bool TryParse(string? input, out int score)
    {
        return int.TryParse(input, out score) && score is >= 0 and <= 100;
    }
}

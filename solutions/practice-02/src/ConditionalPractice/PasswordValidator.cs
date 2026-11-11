namespace ConditionalPractice;

/// <summary>
/// Проверка формальных требований к паролю из примера практической работы 2.
/// </summary>
public static class PasswordValidator
{
    public const int MinLength = 8;
    private const string SpecialChars = "!@#$%^&*";

    public static bool HasMinLength(string? password) =>
        password is { Length: >= MinLength };

    public static bool HasDigit(string? password) =>
        password?.Any(char.IsDigit) == true;

    public static bool HasUpper(string? password) =>
        password?.Any(char.IsUpper) == true;

    public static bool HasSpecial(string? password) =>
        password?.IndexOfAny(SpecialChars.ToCharArray()) >= 0;

    public static bool IsStrong(string? password) =>
        HasMinLength(password)
        && HasDigit(password)
        && HasUpper(password)
        && HasSpecial(password);
}

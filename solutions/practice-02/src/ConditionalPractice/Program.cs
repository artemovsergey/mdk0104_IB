using ConditionalPractice;

while (true)
{
    Console.Write("Введите пароль (или exit для выхода): ");
    string? password = Console.ReadLine();

    if (password == "exit")
    {
        Console.WriteLine("Проверка завершена.");
        break;
    }

    if (string.IsNullOrEmpty(password))
    {
        Console.WriteLine("Ошибка: пароль не может быть пустым.");
        continue;
    }

    if (PasswordValidator.IsStrong(password))
    {
        Console.WriteLine("Пароль надёжен.");
        break;
    }

    Console.WriteLine("Пароль ненадёжен. Не выполнено:");
    if (!PasswordValidator.HasMinLength(password))
    {
        Console.WriteLine("- минимум 8 символов;");
    }
    if (!PasswordValidator.HasDigit(password))
    {
        Console.WriteLine("- хотя бы одна цифра;");
    }
    if (!PasswordValidator.HasUpper(password))
    {
        Console.WriteLine("- хотя бы одна заглавная буква;");
    }
    if (!PasswordValidator.HasSpecial(password))
    {
        Console.WriteLine("- хотя бы один символ из !@#$%^&*.");
    }
}

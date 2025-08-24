import 'package:flutter/material.dart';

class FamilyRelationDropdown extends StatefulWidget {
  final void Function(String?) onChanged;

  const FamilyRelationDropdown({super.key, required this.onChanged});

  @override
  State<FamilyRelationDropdown> createState() => _FamilyRelationDropdownState();
}

class _FamilyRelationDropdownState extends State<FamilyRelationDropdown> {
  final List<String> _relationOptions = [
    '딸',
    '아들',
    '손자',
    '손녀',
    '증손자',
    '증손녀',
    '친인척',
  ];

  String? _selectedRelation;

  @override
  Widget build(BuildContext context) {
    return DropdownButtonFormField<String>(
      value: _selectedRelation,
      items: _relationOptions.map((relation) {
        return DropdownMenuItem(
          value: relation,
          child: Text(
            relation,
            style: const TextStyle(
              fontSize: 18,
              fontFamily: 'Pretendard',
              fontWeight: FontWeight.w500,
              color: Color(0xFF111111),
            ),
          ),
        );
      }).toList(),
      onChanged: (value) {
        setState(() {
          _selectedRelation = value;
        });
        widget.onChanged(value);
      },
      decoration: InputDecoration(
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 20,
        ),
        hintText: '피보호자와의 관계를 선택해주세요',
        hintStyle: const TextStyle(
          fontSize: 18,
          fontFamily: 'Pretendard',
          color: Color(0xFF888888),
        ),
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(20),
          borderSide: const BorderSide(color: Color(0xFFAEAEAE)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(20),
          borderSide: const BorderSide(color: Color(0xFFAEAEAE)),
        ),
      ),
      icon: const Icon(Icons.arrow_drop_down),
      dropdownColor: Colors.white,
    );
  }
}
